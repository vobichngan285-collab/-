// A harmless CI-only process: filename resembles BaoYi. No DLLs loaded.
using System;
using System.Threading;
class ProbeHost
{
    static int Main()
    {
        Thread.Sleep(25000);
        return 0;
    }
}
