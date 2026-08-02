// Bootstrap.cs - source for "Install locallm.exe".
//
// WHAT IT IS. The single file a new user downloads. It fetches the app from
// GitHub, finds a Python, and hands over to install.py, which does the
// hardware-aware part (graphics card detection, choosing the PyTorch build).
//
// WHY C# AND NOT PyInstaller. This compiles with csc.exe, which is part of
// Windows -- no build toolchain to install, nothing to keep in step, and the
// result is a small native .exe rather than a ~10 MB bundled interpreter. The
// machine that builds a release does not need anything the machine already has.
//
// WHY IT IS THIN, DELIBERATELY. Every decision that needs judgement -- which
// PyTorch build matches the graphics card, which Python versions PyTorch even
// publishes wheels for, what to tell the user when none do -- lives in
// install.py, in one place, tested, and readable by the user who just
// downloaded it. Duplicating any of it here would create a second copy that
// drifts. This file does three mechanical things: download, unpack, launch.
//
// BUILD:  installer\build.ps1
using System;
using System.Diagnostics;
using System.IO;
using System.Net;

class Bootstrap
{
    const string ZipUrl =
        "https://github.com/jonhhjackson-a11y/locallm/archive/refs/heads/main.zip";
    // Matches the project name, so the installed folder is recognisable as the
    // thing that was downloaded. The Desktop shortcut is still called
    // "Train My AI" -- that is the friendly name of the thing you double-click
    // to RUN, and it is the name of the launcher file that ships in the repo.
    const string AppFolderName = "locallm";

    static void Say(string s) { Console.WriteLine(s); }

    static int Fail(string what, string fix)
    {
        Say("");
        Say("  SETUP STOPPED: " + what);
        Say("");
        Say(fix);
        Say("");
        Say("  Press Enter to close.");
        Console.ReadLine();
        return 1;
    }

    // Run a program and wait. Returns its exit code, or -1 if it would not start.
    static int Run(string exe, string args, string workingDir)
    {
        try
        {
            var psi = new ProcessStartInfo(exe, args);
            psi.UseShellExecute = false;
            if (workingDir != null) psi.WorkingDirectory = workingDir;
            using (var p = Process.Start(psi)) { p.WaitForExit(); return p.ExitCode; }
        }
        catch (Exception) { return -1; }
    }

    // Is there a Python at all? install.py decides WHICH Python is usable --
    // that depends on what PyTorch publishes and is not knowable from here.
    static string FindPython()
    {
        string[] candidates = { "py", "python" };
        foreach (string c in candidates)
        {
            try
            {
                var psi = new ProcessStartInfo(c, "--version");
                psi.UseShellExecute = false;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.CreateNoWindow = true;
                using (var p = Process.Start(psi))
                {
                    p.WaitForExit();
                    if (p.ExitCode == 0) return c;
                }
            }
            catch (Exception) { }
        }
        return null;
    }

    static int Main(string[] argv)
    {
        Say("====================================================================");
        Say("  LOCALLM - INSTALLER");
        Say("====================================================================");
        Say("");

        string dest = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            AppFolderName);

        Say("  This will install to:");
        Say("    " + dest);
        Say("");
        Say("  It does not need administrator rights and changes nothing");
        Say("  outside that folder and your Desktop shortcut.");
        Say("");
        Say("  Press Enter to continue, or close this window to stop.");
        Console.ReadLine();

        // ---- 1. Python present at all? -----------------------------------
        Say("[1/3] Looking for Python");
        string py = FindPython();
        if (py == null)
        {
            return Fail(
                "Python is not installed on this computer.",
                "  1. Go to https://www.python.org/downloads/\n" +
                "  2. Download Python (3.10 or newer).\n" +
                "  3. IMPORTANT: tick \"Add python.exe to PATH\".\n" +
                "  4. Run this installer again.");
        }
        Say("      found: " + py);

        // ---- 2. Download and unpack --------------------------------------
        Say("[2/3] Downloading the app");
        string tmpZip = Path.Combine(Path.GetTempPath(), "trainmyai_download.zip");
        try
        {
            // GitHub requires TLS 1.2; the default on older .NET is TLS 1.0 and
            // the download fails with a bare "connection closed" if left alone.
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072;
            using (var wc = new WebClient())
            {
                wc.Headers.Add("User-Agent", "TrainMyAI-Installer");
                wc.DownloadFile(ZipUrl, tmpZip);
            }
        }
        catch (Exception e)
        {
            return Fail("could not download the app (" + e.Message + ")",
                        "  Check your internet connection and try again.");
        }
        Say("      downloaded");

        string staging = Path.Combine(Path.GetTempPath(), "trainmyai_unpack");
        try { if (Directory.Exists(staging)) Directory.Delete(staging, true); }
        catch (Exception) { }

        // Expand-Archive rather than System.IO.Compression: it avoids a
        // reference assembly this build would otherwise need, and PowerShell is
        // present on every supported Windows.
        int rc = Run("powershell",
            "-NoProfile -NonInteractive -Command \"Expand-Archive -LiteralPath '"
            + tmpZip + "' -DestinationPath '" + staging + "' -Force\"", null);
        if (rc != 0)
            return Fail("could not unpack the download (code " + rc + ")",
                        "  Try running the installer again.");

        // GitHub wraps the repo in one folder named <repo>-<branch>.
        string inner = staging;
        string[] subs = Directory.GetDirectories(staging);
        if (subs.Length == 1) inner = subs[0];

        try
        {
            if (!Directory.Exists(dest)) Directory.CreateDirectory(dest);
            foreach (string src in Directory.GetFiles(inner, "*",
                                                      SearchOption.AllDirectories))
            {
                string rel = src.Substring(inner.Length).TrimStart('\\');
                string target = Path.Combine(dest, rel);
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                File.Copy(src, target, true);
            }
        }
        catch (Exception e)
        {
            return Fail("could not write to " + dest + " (" + e.Message + ")",
                        "  Close any open files in that folder and try again.");
        }
        Say("      installed to " + dest);

        // ---- 3. Hand over to install.py ----------------------------------
        Say("[3/3] Setting up for your computer");
        Say("");
        string installPy = Path.Combine(dest, "install.py");
        if (!File.Exists(installPy))
            return Fail("install.py is missing from the download.",
                        "  The download may be incomplete. Try again.");

        rc = Run(py, "\"" + installPy + "\"", dest);
        if (rc != 0)
            return Fail("setup did not finish (code " + rc + ").",
                        "  The messages above say what went wrong.");

        Say("");
        Say("  Press Enter to close.");
        Console.ReadLine();
        return 0;
    }
}
