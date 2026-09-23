"""Intégration avec le système : PowerShell, capture d'écran, voix, presse-papiers, ouverture."""

import base64
import os
import re
import shutil
import subprocess
import sys
import webbrowser

WINDOWS = os.name == "nt"
MAC = sys.platform == "darwin"


def powershell(script, env=None, timeout=120):
    """Exécute un script PowerShell et renvoie (code, sortie). Sortie forcée en UTF-8."""
    script = "[Console]::OutputEncoding=[Text.Encoding]::UTF8;$ProgressPreference='SilentlyContinue';" + script
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()  # évite tout problème de guillemets
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-EncodedCommand", encoded],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env={**os.environ, **(env or {})})
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


_USER32 = (
    "Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class JU{"
    "[DllImport(\"user32.dll\")]public static extern bool SetProcessDPIAware();"
    "[DllImport(\"user32.dll\")]public static extern bool SetCursorPos(int x,int y);"
    "[DllImport(\"user32.dll\")]public static extern void mouse_event(uint f,int dx,int dy,int d,UIntPtr e);}';"
    "[void][JU]::SetProcessDPIAware();"
)


def screenshot(path):
    """Capture tout l'écran dans un PNG (largeur max 1280 px).
    Renvoie (erreur, géométrie) ; la géométrie sert à convertir les coordonnées pour cliquer."""
    if WINDOWS:
        code, out = powershell(
            _USER32 + "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
            "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
            "$g=[System.Drawing.Graphics]::FromImage($bmp);"
            "$g.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size);"
            "$w=[Math]::Min(1280,$b.Width);$h=[int]($b.Height*$w/$b.Width);"
            "$s=New-Object System.Drawing.Bitmap $bmp,$w,$h;"
            "$s.Save($env:JARVIS_OUT,[System.Drawing.Imaging.ImageFormat]::Png);"
            "Write-Output \"GEO $($b.Left) $($b.Top) $($b.Width) $($b.Height) $w $h\"",
            env={"JARVIS_OUT": str(path)})
        m = re.search(r"GEO (-?\d+) (-?\d+) (\d+) (\d+) (\d+) (\d+)", out)
        if code != 0 or not m:
            return out or "échec de la capture", None
        left, top, real_w, real_h, w, h = map(int, m.groups())
        return None, {"left": left, "top": top, "scale": real_w / w, "width": w, "height": h}
    if MAC:
        cmds = [["screencapture", "-x", str(path)]]
    else:
        cmds = [["gnome-screenshot", "-f", str(path)], ["scrot", str(path)],
                ["import", "-window", "root", str(path)]]
    for cmd in cmds:
        if shutil.which(cmd[0]):
            r = subprocess.run(cmd, capture_output=True, text=True)
            return (None, None) if r.returncode == 0 else (r.stderr, None)
    return "Aucun outil de capture d'écran trouvé.", None


def click(x, y, button="left", double=False):
    if not WINDOWS:
        return "Le contrôle de la souris n'est disponible que sous Windows."
    down, up = (0x0008, 0x0010) if button == "right" else (0x0002, 0x0004)
    once = f"[JU]::mouse_event({down},0,0,0,[UIntPtr]::Zero);[JU]::mouse_event({up},0,0,0,[UIntPtr]::Zero);"
    code, out = powershell(_USER32 + f"[void][JU]::SetCursorPos({int(x)},{int(y)});Start-Sleep -m 80;"
                           + once + ("Start-Sleep -m 60;" + once if double else ""))
    return None if code == 0 else out


def scroll(amount):
    if not WINDOWS:
        return "Le contrôle de la souris n'est disponible que sous Windows."
    code, out = powershell(_USER32 + f"[JU]::mouse_event(0x0800,0,0,{int(amount) * 120},[UIntPtr]::Zero)")
    return None if code == 0 else out


def send_keys(keys):
    """Touches au format SendKeys : ^c (Ctrl+C), %{TAB} (Alt+Tab), {ENTER}, {F5}…"""
    if not WINDOWS:
        return "Le contrôle du clavier n'est disponible que sous Windows."
    code, out = powershell("Add-Type -AssemblyName System.Windows.Forms;"
                           "[System.Windows.Forms.SendKeys]::SendWait($env:JARVIS_KEYS)",
                           env={"JARVIS_KEYS": keys})
    return None if code == 0 else out


def type_text(text):
    """Tape un texte (via le presse-papiers, fiable pour les accents et les longs textes)."""
    if not WINDOWS:
        return "La saisie au clavier n'est disponible que sous Windows."
    code, out = powershell("Add-Type -AssemblyName System.Windows.Forms;"
                           "Set-Clipboard -Value $env:JARVIS_TEXT;Start-Sleep -m 100;"
                           "[System.Windows.Forms.SendKeys]::SendWait('^v')",
                           env={"JARVIS_TEXT": text})
    return None if code == 0 else out


def notify(title, message):
    """Notification Windows (bulle en bas à droite de l'écran)."""
    if WINDOWS:
        code, out = powershell(
            "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
            "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime]|Out-Null;"
            "$x=New-Object Windows.Data.Xml.Dom.XmlDocument;"
            "$e=[Security.SecurityElement];"
            "$x.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>'+$e::Escape($env:JARVIS_T)+"
            "'</text><text>'+$e::Escape($env:JARVIS_M)+'</text></binding></visual><audio src=\"ms-winsoundevent:Notification.Reminder\"/></toast>');"
            "$app='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show("
            "[Windows.UI.Notifications.ToastNotification]::new($x))",
            env={"JARVIS_T": title, "JARVIS_M": message})
        return None if code == 0 else out
    for cmd in (["notify-send", title, message],
                ["osascript", "-e", f'display notification "{message}" with title "{title}"']):
        if shutil.which(cmd[0]):
            subprocess.run(cmd)
            return None
    return "Notifications indisponibles."


def clean_for_speech(text):
    text = re.sub(r"```.*?```", " (bloc de code) ", text, flags=re.S)
    text = re.sub(r"[*_`#>|]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()[:2000]


def speak(text):
    text = clean_for_speech(text)
    if not text:
        return None
    if WINDOWS:
        code, out = powershell(
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$v=$s.GetInstalledVoices()|?{$_.VoiceInfo.Culture.Name -like 'fr*'}|select -First 1;"
            "if($v){$s.SelectVoice($v.VoiceInfo.Name)};$s.Rate=1;$s.Speak($env:JARVIS_TEXT)",
            env={"JARVIS_TEXT": text}, timeout=600)
        return None if code == 0 else out
    for cmd in (["say", text], ["spd-say", "-w", "-l", "fr", text], ["espeak", "-v", "fr", text]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd)
            return None
    return "Aucun moteur de synthèse vocale trouvé."


def listen(seconds=10):
    """Reconnaissance vocale hors ligne de Windows. Renvoie (texte, erreur)."""
    if not WINDOWS:
        return None, "La dictée vocale en terminal n'est disponible que sous Windows (utilise l'interface web)."
    code, out = powershell(
        "Add-Type -AssemblyName System.Speech;"
        "try{$r=New-Object System.Speech.Recognition.SpeechRecognitionEngine("
        "[System.Globalization.CultureInfo]::GetCultureInfo('fr-FR'))}"
        "catch{$r=New-Object System.Speech.Recognition.SpeechRecognitionEngine};"
        "$r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));"
        "$r.SetInputToDefaultAudioDevice();"
        f"$res=$r.Recognize([TimeSpan]::FromSeconds({int(seconds)}));"
        "if($res){$res.Text}", timeout=seconds + 30)
    if code != 0:
        return None, ("Reconnaissance vocale indisponible. Active-la dans Paramètres > Heure et langue > "
                      "Voix (module vocal français). Détail : " + out[:300])
    return out or None, None if out else "Je n'ai rien entendu."


def clipboard_get():
    if WINDOWS:
        return powershell("Get-Clipboard -Raw")[1]
    cmd = ["pbpaste"] if MAC else ["xclip", "-selection", "clipboard", "-o"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def clipboard_set(text):
    if WINDOWS:
        return powershell("Set-Clipboard -Value $env:JARVIS_TEXT", env={"JARVIS_TEXT": text})[1]
    cmd = ["pbcopy"] if MAC else ["xclip", "-selection", "clipboard"]
    subprocess.run(cmd, input=text, text=True)
    return ""


def open_item(target):
    """Ouvre une URL, un fichier, un dossier ou une application (ex: 'notepad', 'excel')."""
    if re.match(r"^[a-z]+://", target) or target.startswith("www."):
        webbrowser.open(target if "://" in target else "https://" + target)
    elif WINDOWS:
        os.startfile(target)
    else:
        subprocess.Popen(["open" if MAC else "xdg-open", target])
