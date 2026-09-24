"""Lecture (IMAP) et envoi (SMTP) d'e-mails avec la bibliothèque standard."""

import email
import email.utils
import html
import imaplib
import re
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage

# domaine -> (serveur IMAP, serveur SMTP, port SMTP)
SERVERS = {
    ("gmail.com", "googlemail.com"): ("imap.gmail.com", "smtp.gmail.com", 465),
    ("outlook.com", "outlook.fr", "hotmail.com", "hotmail.fr", "live.com", "live.fr", "msn.com"):
        ("outlook.office365.com", "smtp-mail.outlook.com", 587),
    ("yahoo.com", "yahoo.fr"): ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 465),
    ("orange.fr", "wanadoo.fr"): ("imap.orange.fr", "smtp.orange.fr", 465),
    ("free.fr",): ("imap.free.fr", "smtp.free.fr", 465),
    ("sfr.fr", "neuf.fr"): ("imap.sfr.fr", "smtp.sfr.fr", 465),
    ("laposte.net",): ("imap.laposte.net", "smtp.laposte.net", 465),
    ("icloud.com", "me.com"): ("imap.mail.me.com", "smtp.mail.me.com", 587),
    ("gmx.fr", "gmx.com", "gmx.net"): ("imap.gmx.com", "mail.gmx.com", 465),
}


def servers_for(address):
    domain = address.rsplit("@", 1)[-1].lower()
    for domains, conf in SERVERS.items():
        if domain in domains:
            return conf
    return (f"imap.{domain}", f"smtp.{domain}", 465)


def _conf(cfg):
    e = cfg.get("email") or {}
    if not e.get("address") or not e.get("password"):
        raise RuntimeError("Aucune boîte mail configurée. Ouvre Réglages > E-mail dans Jarvis.")
    imap, smtp, port = servers_for(e["address"])
    return e["address"], e["password"], e.get("imap") or imap, e.get("smtp") or smtp, int(e.get("smtp_port") or port)


def _h(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _body(msg):
    plain, rich, files = "", "", []
    for part in msg.walk():
        if part.is_multipart():
            continue
        name = part.get_filename()
        if name:
            files.append(_h(name))
            continue
        payload = part.get_payload(decode=True) or b""
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/plain" and not plain:
            plain = text
        elif part.get_content_type() == "text/html" and not rich:
            rich = text
    if not plain and rich:
        rich = re.sub(r"(?is)<(script|style|head).*?</\1>", "", rich)
        plain = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", rich)))
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", plain)).strip(), files


def _connect(cfg, folder):
    address, password, host, _, _ = _conf(cfg)
    box = imaplib.IMAP4_SSL(host, timeout=30)
    try:
        box.login(address, password)
    except imaplib.IMAP4.error as e:
        box.logout()
        raise RuntimeError(f"Connexion refusée ({e}). Il faut en général un « mot de passe d'application » "
                           "et non ton mot de passe habituel (voir Réglages > E-mail).")
    status, _ = box.select(f'"{folder}"', readonly=True)
    if status != "OK":
        box.logout()
        raise RuntimeError(f"Dossier introuvable : {folder}")
    return box


def list_emails(cfg, count=10, unread_only=False, query="", folder="INBOX"):
    box = _connect(cfg, folder)
    try:
        _, data = box.uid("search", None, "UNSEEN" if unread_only else "ALL")
        uids = data[0].split()
        scan = uids[-(count * 5 if query else count):][::-1]
        out = []
        for uid in scan:
            _, msg_data = box.uid("fetch", uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            raw = next((p[1] for p in msg_data if isinstance(p, tuple)), b"")
            flags = b" ".join(p[0] if isinstance(p, tuple) else p for p in msg_data)
            h = email.message_from_bytes(raw)
            line = (f"[uid {uid.decode()}] {'' if b'Seen' in flags else '(NON LU) '}"
                    f"{_h(h['Date'])[:25]} · {_h(h['From'])} · {_h(h['Subject'])}")
            if query and query.lower() not in line.lower():
                continue
            out.append(line)
            if len(out) >= count:
                break
        return "\n".join(out) or "(aucun e-mail)"
    finally:
        box.logout()


def read_email(cfg, uid, folder="INBOX"):
    box = _connect(cfg, folder)
    try:
        _, msg_data = box.uid("fetch", str(uid).encode(), "(BODY.PEEK[])")
        raw = next((p[1] for p in msg_data if isinstance(p, tuple)), None)
        if not raw:
            return "ERREUR : e-mail introuvable."
        msg = email.message_from_bytes(raw)
        body, files = _body(msg)
        return (f"De : {_h(msg['From'])}\nÀ : {_h(msg['To'])}\nDate : {_h(msg['Date'])}\n"
                f"Objet : {_h(msg['Subject'])}\n"
                + (f"Pièces jointes : {', '.join(files)}\n" if files else "") + f"\n{body}")
    finally:
        box.logout()


def send_email(cfg, to, subject, body):
    address, password, _, host, port = _conf(cfg)
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = address, to, subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg.set_content(body)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as s:
            s.login(address, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=context)
            s.login(address, password)
            s.send_message(msg)
