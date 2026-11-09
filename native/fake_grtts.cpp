// CI test fake ONLY; never copied to user's product ZIP.
#include <windows.h>
#include <cmath>
#include <cstdint>
#include <vector>
#include <cwchar>
static std::vector<int16_t> pcm;
extern "C" {
__declspec(dllexport) bool YongDe_Initialize() { return true; }
__declspec(dllexport) void YongDe_Uninitialize() {}
__declspec(dllexport) int YongDe_GetVoiceCount() { return 1; }
__declspec(dllexport) int YongDe_GetVoiceName(int n,wchar_t* b,int sz) {
    if(n!=0||!b||sz<1)return 0;
    wcscpy_s(b,sz,L"Native Host Test Voice");
    return 1;
}
__declspec(dllexport) bool YongDe_SetVoice(int n) { return n==0; }
__declspec(dllexport) void YongDe_GetAudioFormat(int* sr,int* bits,int* chan) {
    *sr=24000;*bits=16;*chan=1;
}
__declspec(dllexport) bool YongDe_TextToAudio(const wchar_t* text, void** dest, int* size) {
    if(!text||!dest||!size)return false;
    pcm.resize(4800);
    for(int i=0;i<4800;i++)pcm[i]=static_cast<int16_t>(std::sin(i*0.30)*5000);
    *dest=pcm.data();
    *size=static_cast<int>(pcm.size()*sizeof(int16_t));
    return true;
}
__declspec(dllexport) void YongDe_FreeAudio(void*) {}
__declspec(dllexport) void YongDe_SetRate(int) {}
__declspec(dllexport) void YongDe_SetVolume(int) {}
}
