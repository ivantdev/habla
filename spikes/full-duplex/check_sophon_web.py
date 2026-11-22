"""Comprobación opcional de la interfaz real con Chromium y micrófono sintético.

Requiere Playwright + Chromium, el servidor listo y ninguna otra sesión.
"""

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from playwright.async_api import async_playwright

from bench_sophon import RATE, speech


async def run(directory):
    directory.mkdir(parents=True, exist_ok=False)
    audio = speech("I like pizza with mushrooms.", "en", directory)
    capture = directory / "microphone.wav"
    sf.write(capture, np.concatenate([np.zeros(RATE * 2), audio, np.zeros(RATE * 25)]), RATE)
    instructions = "You are an English conversation partner. Talk only about restaurants. React to what I say and ask one brief question. Do not correct me."
    report = {"physical_microphone_tested": False, "speaker_listened": False, "errors": [], "events": {}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
            f"--use-file-for-fake-audio-capture={capture.resolve()}", "--autoplay-policy=no-user-gesture-required"])
        context = await browser.new_context(permissions=["microphone"], accept_downloads=True)
        page = await context.new_page()
        page.on("pageerror", lambda e: report["errors"].append(str(e)))

        def socket(ws):
            def sent(raw):
                ev = json.loads(raw)
                if ev["type"] == "session.update":
                    report["sent_instructions"] = ev["session"]["instructions"]
            def received(raw):
                ev = json.loads(raw)
                name = ev["type"]
                report["events"][name] = report["events"].get(name, 0) + 1
            ws.on("framesent", sent)
            ws.on("framereceived", received)
        page.on("websocket", socket)
        await page.goto("http://127.0.0.1:8999")
        await page.wait_for_function("!document.getElementById('start').disabled")
        report["default_profile"] = await page.locator("#profile").input_value()
        await page.locator("#instructions").fill(instructions)
        await page.evaluate("window.maxMic = 0; setInterval(() => window.maxMic = Math.max(window.maxMic, document.getElementById('level').value), 20)")
        await page.locator("#start").click()
        await page.wait_for_function("rows.length > 0 && document.getElementById('text').textContent.length > 15", timeout=60000)
        report["active"] = await page.evaluate("({context:ctx.state, microphone:stream.getTracks()[0].readyState, maxMic:window.maxMic, transcript:document.getElementById('text').textContent, scheduledSources:active.size})")
        await page.locator("#stop").click()
        await page.wait_for_function("ctx.state === 'closed' && !document.getElementById('start').disabled")
        report["stopped"] = await page.evaluate("({context:ctx.state, microphone:stream.getTracks()[0].readyState, sources:active.size, status:document.getElementById('status').textContent})")
        async with page.expect_download() as dl:
            await page.locator("#export").click()
        download = await dl.value
        await download.save_as(directory / "browser-metrics.json")
        metrics = json.loads((directory / "browser-metrics.json").read_text())
        report["exported_rows"] = len(metrics["rows"])
        report["exported_tutor_text_matches"] = metrics["tutor_text_received"] == await page.locator("#text").text_content()
        report["instructions_match"] = report.get("sent_instructions") == metrics["session"]["instructions"] == instructions
        # Permission denial must leave controls usable and the audio context closed.
        denied = await context.new_page()
        await denied.add_init_script("navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied for test', 'NotAllowedError'); }")
        await denied.goto("http://127.0.0.1:8999")
        await denied.wait_for_function("!document.getElementById('start').disabled")
        await denied.locator("#start").click()
        await denied.wait_for_function("document.getElementById('status').textContent.includes('Permite el micrófono')")
        report["denied"] = await denied.evaluate("({context:ctx.state, startEnabled:!document.getElementById('start').disabled, status:document.getElementById('status').textContent})")
        await page.screenshot(path=str(directory / "interface.png"), full_page=True)
        await browser.close()
    (directory / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    assert not report["errors"], report
    assert report["instructions_match"] and report["active"]["maxMic"] > 0.0125, report
    assert report["exported_tutor_text_matches"], report
    assert report["active"]["context"] == "running" and report["active"]["microphone"] == "live", report
    assert report["stopped"]["context"] == "closed" and report["stopped"]["microphone"] == "ended" and report["stopped"]["sources"] == 0, report
    assert report["denied"]["context"] == "closed" and report["denied"]["startEnabled"], report
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
