// capture-cli/Program.cs
// dotnet publish -c Release -r win-x64 --self-contained -p:PublishSingleFile=true
using System;
using System.IO;
using System.Runtime.InteropServices;
using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace WinLoopCap
{
    internal class Program
    {
        static void Main(string[] args)
        {
            const int sampleRate = 48000;
            const int channels   = 2;
            var device = GetDefaultRenderDevice();
            using var capture = new WasapiLoopbackCapture(device)
            {
                WaveFormat = new WaveFormat(sampleRate, 16, channels)
            };
            capture.DataAvailable += (_, e) =>
            {
                Console.OpenStandardOutput().Write(e.Buffer, 0, e.BytesRecorded);
            };
            capture.StartRecording();
            Console.CancelKeyPress += (_, e) =>
            {
                capture.StopRecording();
                e.Cancel = true;
            };
            capture.RecordingStopped += (_, _) => Environment.Exit(0);
            System.Threading.Thread.Sleep(-1);
        }

        static MMDevice GetDefaultRenderDevice()
        {
            using var enumerator = new MMDeviceEnumerator();
            return enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
        }
    }
}