import asyncio
from os import getenv

from telethon import Button
from .helpers import auth_chat_only, run_shell, get_size, hnd
from .db import add_download_to_db, get_download_list, remove_download_from_db
from requests import get

import aria2p as aria2

PORT = int(getenv("PORT", 6800))


def setup_aria():
    trackers_list = get(
        "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
    ).text.replace("\n\n", ",")
    trackers = f"[{trackers_list}]"
    cmd = f"aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port={PORT} --max-connection-per-server=10 --rpc-max-request-size=1024M --check-certificate=false --follow-torrent=mem --seed-time=600 --max-upload-limit=0 --max-concurrent-downloads=1 --min-split-size=10M --follow-torrent=mem --split=10 --bt-tracker={trackers} --daemon=true --allow-overwrite=true"
    run_shell(cmd, wait=False)


setup_aria()
ARIA = aria2.API(aria2.Client(host="http://localhost", port=PORT, secret=""))


def add_download(chat_id, url, path):
    download = ARIA.add_magnet(url, options={"dir": path}) if url.startswith("magnet:") else ARIA.add_uris([url], options={"dir": path})
    add_download_to_db(chat_id, download.gid)
    return download


def get_path_from_chat_id(chat_id):
    return f"/downloads/{chat_id}/"


def get_len_downloads():
    return len(get_download_list())


def get_download_gids():
    downloads = ARIA.get_downloads()
    return [d.gid for d in downloads]


def gen_progress_msg(chat_id: int, status):
    msg = f"Downloading: {status.name}"
    msg += f"\nSpeed: {get_size(status.download_speed)}/s"
    msg += "\nETA: " + status.eta_string(precision=0)
    msg += f"\nTotal: {get_size(status.total_length)}"
    msg += f"\nProgress: {status.progress_string(digits=2)}"
    buttons = [
        [Button.inline("Cancel", data=f"cancel_{chat_id}_{status.gid}")],
        [Button.inline("Pause", data=f"pause_{chat_id}_{status.gid}")],
    ]
    return msg, buttons


async def progress_callback(gid: str, msg):
    finished = False
    print(f"Progress callback for {gid}")
    while not finished:
        status = ARIA.get_download(gid)
        print(f"Status: {status.status}")
        if status.status == "complete":
            print(str(status))
        elif status.status == "error":
            finished = True
            msg = await msg.edit("Download failed." +
                                 f"\nError: {status.error_message}")
            remove_download_from_db(msg.chat_id, gid)
        elif status.status == "paused":
            finished = True
            msg = await msg.edit("Download paused.")
        elif status.status == "active":
            print(f"Progress: {status.progress}")
            text, buttons = gen_progress_msg(msg.chat_id, status)
            if msg.text != text:
                msg = await msg.edit(text, buttons=buttons)
            await asyncio.sleep(3)
        elif status.status == "waiting":
            text, buttons = gen_progress_msg(msg.chat_id, status)
            if msg.text != text:
                msg = await msg.edit(text, buttons=buttons)
            await asyncio.sleep(3)
        elif status.status == "stopped":
            buttons = [
                [Button.inline("Resume", data=f"start_{msg.chat_id}_{gid}")],
                [Button.inline("Delete", data=f"delete_{msg.chat_id}_{gid}")],
            ]
            msg = await msg.edit(
                f"Download stopped.",
                buttons=buttons,
            )
            finished = True
        else:
            msg = await msg.edit(f"Unknown status: {status.status}")
            finished = True


@hnd(pattern="download")
@auth_chat_only  # only allow users in the chat to download
async def download_cmd(ev):
    try:
        url = ev.text.split(" ", 1)[1]
    except IndexError:
        return await ev.reply("No URL provided")
    path = get_path_from_chat_id(ev.chat_id)
    download = add_download(ev.chat_id, url, path)
    msg = await ev.reply("`Downloading...`")
    print(f"Downloading {url} to {path}")
    await progress_callback(download.gid, msg)
