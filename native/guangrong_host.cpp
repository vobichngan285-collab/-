// Independent Windows Guangrong engine host. No Python/PyInstaller runtime.
// Loads original publisher DLL from its own directory; no BaoYi/NVDA API calls.
// Pipe protocol: HELLO/VOICE/READY/ERROR; commands VOICE/RATE/VOL/STOP/SPEAK/QUIT.
// SPEAK contains base64 UTF-8 text; AUDIO header is followed by exact PCM bytes.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <wincrypt.h>
#include <io.h>
#include <fcntl.h>
#include <atomic>
#include <algorithm>
#include <condition_variable>
#include <cstring>
#include <cstdio>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#pragma comment(lib, "Crypt32.lib")

namespace {
void debug_stage(const char* label) {
    wchar_t destination[4096]={};
    DWORD length=GetEnvironmentVariableW(L"GR_NATIVE_DEBUG_FILE",destination,4096);
    if (length==0 || length>=4096) return;
    FILE* fp=nullptr;
    if (_wfopen_s(&fp,destination,L"ab")==0 && fp) {
        fwrite(label,1,strlen(label),fp);
        fwrite("\\n",1,1,fp);
        fclose(fp);
    }
}
std::mutex output_mutex;
void send_line(const std::string& s) {
    std::lock_guard<std::mutex> g(output_mutex);
    std::cout << s << "\n" << std::flush;
}
std::string b64encode(const std::string& input) {
    DWORD needed = 0;
    if (!CryptBinaryToStringA(reinterpret_cast<const BYTE*>(input.data()),
        static_cast<DWORD>(input.size()), CRYPT_STRING_BASE64 | CRYPT_STRING_NOCRLF,
        nullptr, &needed)) return "";
    std::string output(needed, '\0');
    if (!CryptBinaryToStringA(reinterpret_cast<const BYTE*>(input.data()),
        static_cast<DWORD>(input.size()), CRYPT_STRING_BASE64 | CRYPT_STRING_NOCRLF,
        output.data(), &needed)) return "";
    output.resize(std::strlen(output.c_str()));
    return output;
}
std::string b64decode(const std::string& input) {
    DWORD needed = 0;
    if (!CryptStringToBinaryA(input.c_str(), static_cast<DWORD>(input.size()),
        CRYPT_STRING_BASE64, nullptr, &needed, nullptr, nullptr)) return "";
    std::string result(needed, '\0');
    if (!CryptStringToBinaryA(input.c_str(), static_cast<DWORD>(input.size()),
        CRYPT_STRING_BASE64, reinterpret_cast<BYTE*>(result.data()), &needed,
        nullptr, nullptr)) return "";
    result.resize(needed);
    return result;
}
std::string to_utf8(const std::wstring& in) {
    if (in.empty()) return "";
    int len=WideCharToMultiByte(CP_UTF8, 0, in.data(), static_cast<int>(in.size()),
                               nullptr, 0, nullptr, nullptr);
    if (len <= 0) return "";
    std::string s(len, '\0');
    WideCharToMultiByte(CP_UTF8,0,in.data(),static_cast<int>(in.size()),
                        s.data(),len,nullptr,nullptr);
    return s;
}
std::wstring to_wide(const std::string& in) {
    if (in.empty()) return L"";
    int len=MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, in.data(),
                               static_cast<int>(in.size()),nullptr,0);
    if (len <= 0) return L"";
    std::wstring s(len, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, in.data(),
                        static_cast<int>(in.size()),s.data(),len);
    return s;
}
template <typename T> T get_symbol(HMODULE h, const char *name) {
    return reinterpret_cast<T>(GetProcAddress(h, name));
}
struct Engine {
    HMODULE module = nullptr;
    bool (*initialize)() = nullptr;
    void (*uninitialize)() = nullptr;
    int (*voice_count)() = nullptr;
    int (*voice_name)(int,wchar_t*,int) = nullptr;
    bool (*select_voice)(int) = nullptr;
    void (*audio_format)(int*,int*,int*) = nullptr;
    bool (*synthesize)(const wchar_t*,void**,int*) = nullptr;
    void (*free_audio)(void*) = nullptr;
    void (*set_rate)(int) = nullptr;
    void (*set_volume)(int) = nullptr;
    bool initialized = false;
    std::mutex native_lock;
    ~Engine() {
        if (initialized && uninitialize) uninitialize();
        if (module) FreeLibrary(module);
    }
    bool start(const std::wstring& dll) {
        // The parent EXE is frozen and may have changed its DLL search path;
        // the native helper must not inherit that third-party path.
        debug_stage("native-before-reset-dlldir");
        SetDllDirectoryW(nullptr);
        debug_stage("native-after-reset-dlldir");
        debug_stage("native-before-load-library-ex");
        module = LoadLibraryExW(dll.c_str(), nullptr,
                               LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR |
                               LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        debug_stage("native-after-load-library-ex");
        if (!module) {
            send_line("ERROR\t" + std::to_string(GetLastError()) +
                      "\tWindows DLL loader rejected the publisher engine");
            return false;
        }
        initialize=get_symbol<decltype(initialize)>(module,"YongDe_Initialize");
        uninitialize=get_symbol<decltype(uninitialize)>(module,"YongDe_Uninitialize");
        voice_count=get_symbol<decltype(voice_count)>(module,"YongDe_GetVoiceCount");
        voice_name=get_symbol<decltype(voice_name)>(module,"YongDe_GetVoiceName");
        select_voice=get_symbol<decltype(select_voice)>(module,"YongDe_SetVoice");
        audio_format=get_symbol<decltype(audio_format)>(module,"YongDe_GetAudioFormat");
        synthesize=get_symbol<decltype(synthesize)>(module,"YongDe_TextToAudio");
        free_audio=get_symbol<decltype(free_audio)>(module,"YongDe_FreeAudio");
        set_rate=get_symbol<decltype(set_rate)>(module,"YongDe_SetRate");
        set_volume=get_symbol<decltype(set_volume)>(module,"YongDe_SetVolume");
        if (!initialize || !uninitialize || !voice_count || !voice_name ||
            !select_voice || !audio_format || !synthesize || !free_audio ||
            !set_rate || !set_volume) {
            send_line("ERROR\t127\tOfficial DLL does not expose required TTS functions");
            return false;
        }
        initialized=initialize();
        if (!initialized) {
            send_line("ERROR\t1114\tOfficial DLL initialization returned false");
            return false;
        }
        int count=std::clamp(voice_count(),0,256);
        send_line("HELLO\t"+std::to_string(count));
        for(int n=0;n<count;++n) {
            wchar_t buf[256] = {};
            voice_name(n,buf,255);
            send_line("VOICE\t"+std::to_string(n)+"\t"+b64encode(to_utf8(buf)));
        }
        send_line("READY");
        return true;
    }
};
struct Request { uint64_t generation; std::wstring text; };
}

int wmain(int argc, wchar_t** argv) {
    debug_stage("native-wmain-entry");
    _setmode(_fileno(stdin),_O_BINARY);
    debug_stage("native-before-setmode");
    _setmode(_fileno(stdout),_O_BINARY);
    debug_stage("native-before-sync-io");
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    if (argc!=3 || std::wstring(argv[1])!=L"--server") {
        send_line("ERROR\t2\tUsage: GuangrongHost.exe --server <grtts_x64.dll>");
        return 2;
    }
    debug_stage("native-before-engine");
    Engine engine;
    if (!engine.start(argv[2])) return 3;
    debug_stage("native-after-engine");

    std::atomic<uint64_t> generation{0};
    std::mutex queue_mutex;
    std::condition_variable ready;
    bool running=true, pending=false;
    Request request{0,L""};

    std::thread worker([&] {
        while(true) {
            Request todo{};
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                ready.wait(lock,[&] {return !running || pending;});
                if (!running) return;
                todo=request;
                pending=false;
            }
            if(todo.generation != generation.load()) continue;
            std::vector<char> pcm;
            int sr=0,bits=0,channels=0;
            bool ok=false;
            {
                std::lock_guard<std::mutex> lock(engine.native_lock);
                if(todo.generation != generation.load()) continue;
                void* address=nullptr;
                int length=0;
                ok=engine.synthesize(todo.text.c_str(),&address,&length);
                if (ok && address && length>0 && length<=32*1024*1024) {
                    engine.audio_format(&sr,&bits,&channels);
                    pcm.assign(reinterpret_cast<char*>(address),
                               reinterpret_cast<char*>(address)+length);
                }
                if (address) engine.free_audio(address);
            }
            if(todo.generation != generation.load()) continue;
            if(!ok || pcm.empty() || sr<=0 || (bits!=16&&bits!=8&&bits!=24&&bits!=32) ||
               (channels!=1&&channels!=2)) {
                send_line("ERROR\t6\tVendor synthesis did not return valid PCM");
                continue;
            }
            std::lock_guard<std::mutex> guard(output_mutex);
            std::cout << "AUDIO\t" << todo.generation << "\t" << sr << "\t"
                      << bits << "\t" << channels << "\t" << pcm.size() << "\n";
            std::cout.write(pcm.data(),static_cast<std::streamsize>(pcm.size()));
            std::cout.flush();
        }
    });
    std::string line;
    while(std::getline(std::cin,line)) {
        if(!line.empty()&&line.back()=='\r')line.pop_back();
        size_t tab=line.find('\t');
        std::string command=line.substr(0,tab);
        std::string payload=tab==std::string::npos?"":line.substr(tab+1);
        if(command=="QUIT")break;
        if(command=="STOP") {
            generation.fetch_add(1);
            std::lock_guard<std::mutex> lock(queue_mutex);
            pending=false;
        } else if(command=="VOICE" || command=="RATE" || command=="VOL") {
            int n=0;
            try { n=std::stoi(payload); } catch(...) {continue;}
            std::lock_guard<std::mutex> lock(engine.native_lock);
            if(command=="VOICE")engine.select_voice(n);
            else if(command=="RATE")engine.set_rate(std::clamp(n,0,100));
            else engine.set_volume(std::clamp(n,0,100));
        } else if(command=="SPEAK") {
            size_t split=payload.find('\t');
            if(split==std::string::npos)continue;
            uint64_t id=0;
            try {id=std::stoull(payload.substr(0,split));}
            catch(...) {continue;}
            std::wstring spoken=to_wide(b64decode(payload.substr(split+1)));
            if(spoken.empty() || spoken.size()>4000)continue;
            generation.store(id);
            {
                std::lock_guard<std::mutex> lock(queue_mutex);
                request={id,std::move(spoken)};
                pending=true;
            }
            ready.notify_one();
        }
    }
    generation.fetch_add(1);
    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        running=false;
        pending=false;
    }
    ready.notify_all();
    // Speech synthesis may block inside publisher DLL. Parent process enforces
    // a bounded close timeout and can terminate helper if this join stalls.
    worker.join();
    return 0;
}
