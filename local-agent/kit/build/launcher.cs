// Lanceur de Photo Studio IA : démarre l'application (Python embarqué) sans fenêtre de console.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Launcher
{
    [STAThread]
    static void Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(dir, "runtime", "pythonw.exe");
        string app = Path.Combine(dir, "app", "kit", "kit.py");
        try
        {
            var psi = new ProcessStartInfo(python, "\"" + app + "\"");
            psi.WorkingDirectory = dir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            Process.Start(psi);
        }
        catch (Exception e)
        {
            MessageBox.Show("Impossible de démarrer Photo Studio IA :\n" + e.Message, "Photo Studio IA",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
