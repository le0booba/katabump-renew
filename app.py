#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import requests
from seleniumbase import SB

# Fetch credentials and Telegram config from environment variables
EMAIL        = os.environ.get("KATABUMP_EMAIL") or ""    # Login email
PASSWORD     = os.environ.get("KATABUMP_PASSWORD") or "" # Account password
TG_CHAT_ID   = os.environ.get("TG_CHAT_ID") or ""        # TG notification chat id (optional)
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or ""      # TG notification bot token (optional)

BASE_URL = "https://dashboard.katabump.com"  # Website URL

# Telegram Notification Module
def send_tg_message(status_icon, status_text, time_left=""):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("ℹ️ TG_BOT_TOKEN or TG_CHAT_ID is not configured, skipping Telegram notification.")
        return

    # Get Beijing Time (UTC+8)
    local_time = time.gmtime(time.time() + 8 * 3600)
    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)

    # Email masking: keep first 2 and last 2 characters of username, mask middle with ****
    if '@' in EMAIL:
        name, domain = EMAIL.split('@', 1)
        if len(name) > 4:
            masked_email = f"{name[:2]}****{name[-2:]}@{domain}"
        else:
            masked_email = f"{name}@{domain}"
    else:
        masked_email = EMAIL[:2] + '****'

    text = (
        f"🇫🇷 Katabump Renewal Notification\n\n"
        f"{status_icon} {status_text}\n"
        f"👤 Renewed Account: {masked_email}\n"
        f"⏱️ Renewal Time: {current_time_str}"
    )

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("📩 Telegram notification sent successfully!")
        else:
            print(f"⚠️ Failed to send Telegram notification: {r.text}")
    except Exception as e:
        print(f"⚠️ Exception occurred while sending Telegram notification: {e}")

# Page Injection Scripts
_EXPAND_JS = """
(function() {
    var ts = document.querySelector('input[name="cf-turnstile-response"]');
    if (!ts) return 'no-turnstile';
    var el = ts;
    for (var i = 0; i < 20; i++) {
        el = el.parentElement;
        if (!el) break;
        var s = window.getComputedStyle(el);
        if (s.overflow === 'hidden' || s.overflowX === 'hidden' || s.overflowY === 'hidden')
            el.style.overflow = 'visible';
        el.style.minWidth = 'max-content';
    }
    document.querySelectorAll('iframe').forEach(function(f){
        if (f.src && f.src.includes('challenges.cloudflare.com')) {
            f.style.width = '300px'; f.style.height = '65px';
            f.style.minWidth = '300px';
            f.style.visibility = 'visible'; f.style.opacity = '1';
        }
    });
    return 'done';
})()
"""

_EXISTS_JS = """
(function(){
    return document.querySelector('input[name="cf-turnstile-response"]') !== null;
})()
"""

_SOLVED_JS = """
(function(){
    var i = document.querySelector('input[name="cf-turnstile-response"]');
    return !!(i && i.value && i.value.length > 20);
})()
"""

_WININFO_JS = """
(function(){
    return {
        sx: window.screenX || 0,
        sy: window.screenY || 0,
        oh: window.outerHeight,
        ih: window.innerHeight
    };
})()
"""

# ===== Auto-Renewal Related =====

# Locate iframe inside modal, expand it, and return click coordinates
_ALTCHA_EXPAND_JS = """
(function() {
    var modal = document.querySelector('div.modal.show') || document;
    var iframes = modal.querySelectorAll('iframe');
    for (var i = 0; i < iframes.length; i++) {
        var r = iframes[i].getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
            iframes[i].style.width  = '300px';
            iframes[i].style.height = '150px';
            iframes[i].style.minWidth  = '300px';
            iframes[i].style.minHeight = '150px';
            iframes[i].style.visibility = 'visible';
            iframes[i].style.opacity = '1';
            var el = iframes[i];
            for (var j = 0; j < 10; j++) {
                el = el.parentElement;
                if (!el) break;
                el.style.overflow = 'visible';
            }
            var r2 = iframes[i].getBoundingClientRect();
            return { cx: Math.round(r2.x + 30), cy: Math.round(r2.y + r2.height / 2) };
        }
    }
    return null;
})()
"""

# Check if ALTCHA verification has passed
_ALTCHA_SOLVED_JS = """
(function(){
    var modal = document.querySelector('div.modal.show') || document;
    // hidden input has a value
    var inputs = modal.querySelectorAll('input[type="hidden"]');
    for (var i = 0; i < inputs.length; i++) {
        var n = (inputs[i].name || '').toLowerCase();
        if ((n.includes('altcha') || n.includes('captcha')) &&
            inputs[i].value && inputs[i].value.length > 20) return true;
    }
    // checkbox becomes disabled
    var cbs = modal.querySelectorAll('input[type="checkbox"]');
    for (var j = 0; j < cbs.length; j++) {
        if (cbs[j].disabled) return true;
    }
    // widget data-state attribute
    var w = modal.querySelector('[data-state="verified"],.altcha--verified,.altcha-verified');
    if (w) return true;
    return false;
})()
"""

# Low-level Input Tool
def js_fill_input(sb, selector: str, text: str):
    safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
    sb.execute_script(f"""
    (function(){{
        var el = document.querySelector('{selector}');
        if (!el) return;
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        if (nativeInputValueSetter) {{
            nativeInputValueSetter.call(el, "{safe_text}");
        }} else {{
            el.value = "{safe_text}";
        }}
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }})()
    """)

def _activate_window():
    for cls in ["chrome", "chromium", "Chromium", "Chrome", "google-chrome"]:
        try:
            r = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", cls], capture_output=True, text=True, timeout=3)
            wids = [w for w in r.stdout.strip().split("\n") if w.strip()]
            if wids:
                subprocess.run(["xdotool", "windowactivate", "--sync", wids[0]], timeout=3, stderr=subprocess.DEVNULL)
                time.sleep(0.2)
                return
        except Exception:
            pass
    try:
        subprocess.run(["xdotool", "getactivewindow", "windowactivate"], timeout=3, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# def _xdotool_click(x: int, y: int):
#     _activate_window()
#     try:
#         subprocess.run(["xdotool", "mousemove", "--sync", str(x), str(y)], timeout=3, stderr=subprocess.DEVNULL)
#         time.sleep(0.15)
#         subprocess.run(["xdotool", "click", "1"], timeout=2, stderr=subprocess.DEVNULL)
#     except Exception:
#         os.system(f"xdotool mousemove {x} {y} click 1 2>/dev/null")

# Captcha Handling (using SeleniumBase built-in uc_gui_click_captcha)
def handle_turnstile(sb) -> bool:
    print("🔍 Handling Cloudflare Turnstile verification...")
    time.sleep(2)

    # Check if already passed silently
    if sb.execute_script(_SOLVED_JS):
        print("✅ Passed silently")
        return True

    # Try expanding Turnstile (to prevent clipping by parent container overflow:hidden)
    for _ in range(3):
        try: sb.execute_script(_EXPAND_JS)
        except Exception: pass
        time.sleep(0.5)

    # Use SeleniumBase built-in uc_gui_click_captcha to handle Turnstile
    # This automatically: detects captcha type -> locates iframe -> calculates coordinates -> performs smooth PyAutoGUI click
    for attempt in range(6):
        if sb.execute_script(_SOLVED_JS):
            print(f"✅ Turnstile passed (Attempt {attempt})")
            return True

        print(f"🖱️ Calling uc_gui_click_captcha (Attempt {attempt + 1})...")
        try:
            sb.uc_gui_click_captcha()
        except Exception as e:
            print(f"⚠️ Exception during uc_gui_click_captcha call: {e}")

        # Wait for verification result (up to 8 seconds)
        for _ in range(16):
            time.sleep(0.5)
            if sb.execute_script(_SOLVED_JS):
                print(f"✅ Turnstile passed (Attempt {attempt + 1})")
                return True

        print(f"⚠️ Attempt {attempt + 1} did not pass, retrying...")

    print("  ❌ Turnstile failed after 6 attempts")
    return False

# Account Login
def login(sb) -> bool:
    print(f"🌐 Opening login page: {BASE_URL}/auth/login")
    sb.uc_open_with_reconnect(BASE_URL + "/auth/login", reconnect_time=8)
    time.sleep(8)

    # Wait for Cloudflare challenge to pass first (up to 30 seconds)
    print("⏳ Waiting for Cloudflare verification to pass...")
    cf_passed = False
    for i in range(30):
        page_src = sb.get_page_source() or ""
        if 'input[name="email"]' in page_src.lower() or 'name="email"' in page_src.lower():
            cf_passed = True
            print(f"✅ Cloudflare verification passed ({i+1}s)")
            break
        time.sleep(1)
    if not cf_passed:
        print("⚠️ Cloudflare verification might not have passed, proceeding anyway...")

    try:
        sb.wait_for_element('input[type="email"]', timeout=15)
    except Exception:
        # Fallback to uppercase selector
        try:
            sb.wait_for_element('input[type="Email"]', timeout=5)
        except Exception:
            print("❌ Login form was not loaded on the page")
            cur_url = sb.get_current_url()
            page_title = sb.get_title() or ""
            print(f"  Current URL: {cur_url}")
            print(f"  Current Title: {page_title}")
            sb.save_screenshot("login_load_fail.png")
            return False

    print("🍪 Dismissing possible Cookie popups...")
    try:
        for btn in sb.find_elements("button"):
            if "Accept" in (btn.text or ""):
                btn.click()
                time.sleep(0.5)
                break
    except Exception:
        pass

    print(f"📧 Entering email...")
    js_fill_input(sb, 'input[type="email"]', EMAIL)
    time.sleep(1)
    
    print("🔑 Entering password...")
    js_fill_input(sb, 'input[type="password"]', PASSWORD)
    time.sleep(3)

    # Wait for Turnstile widget to appear (up to 10 seconds)
    print("⏳ Waiting for Turnstile widget to appear...")
    ts_found = False
    for i in range(10):
        if sb.execute_script(_EXISTS_JS):
            ts_found = True
            print(f"✅ Turnstile detected ({i+1}s)")
            break
        time.sleep(1)

    if ts_found:
        if not handle_turnstile(sb):
            print("❌ Turnstile verification failed on login page")
            sb.save_screenshot("login_turnstile_fail.png")
            return False
    else:
        print("ℹ️ Turnstile not detected")

    print("🖱️ Pressing Enter to submit form...")
    sb.press_keys('input[name="password"]', '\n')

    print("⏳ Waiting for login redirect...")
    for _ in range(12):
        time.sleep(1)
        cur_url = sb.get_current_url().split('?')[0].lower()
        page_title = sb.get_title() or ""
        if cur_url.startswith(f"{BASE_URL}/dashboard") or "Dashboard | KataBump" in page_title.lower():
            break

    cur_url = sb.get_current_url().split('?')[0].lower()
    page_title = sb.get_title() or ""
    if cur_url.startswith(f"{BASE_URL}/dashboard") or "Dashboard | KataBump" in page_title.lower():
        print(f"✅ Login successful! (URL: {sb.get_current_url()}, Title: {page_title})")
        return True
        
    print(f"❌ Login failed; page did not redirect to dashboard. (URL: {sb.get_current_url()}, Title: {page_title})")
    sb.save_screenshot("login_failed.png")
    return False

# ===== Auto-Renewal Flow =====

def _read_alert(sb):
    """Reads the text from the first Bootstrap alert on the page; returns empty string if not found"""
    try:
        el = sb.find_element("div.alert", timeout=4)
        return (el.text or "").strip()
    except Exception:
        return ""


def _goto_server_detail(sb) -> bool:
    """Finds and clicks 'See' on the Dashboard homepage to enter server details"""
    print("\n🖥️  Navigating to server renewal page...")
    time.sleep(5)

    # Check if there is already a global banner indicating renewal is not yet possible
    alert_text = _read_alert(sb)
    if alert_text and "can't renew" in alert_text.lower():
        print(f"ℹ️  Top alert message: {alert_text}")
        send_tg_message("ℹ️", "⚠️ Not renewal time yet", alert_text)
        return False

    # Try multiple selectors to find the 'See' link
    selectors = [
        'a[href*="/servers/edit?id="]',
        'td a[href*="/servers/edit"]',
        'table a[href*="/servers/edit"]',
        'table td a',
    ]

    see_link = None
    for sel in selectors:
        try:
            see_link = sb.find_element(sel, timeout=8)
            print(f"✅ Link found using selector: {sel}")
            break
        except Exception:
            continue

    # If all selectors fail, attempt finding by text content
    if see_link is None:
        print("⚠️ Selectors missed, attempting text match...")
        try:
            for a in sb.find_elements("a"):
                if (a.text or "").strip().lower() == "see":
                    see_link = a
                    print("✅ Link found by text 'See'")
                    break
        except Exception:
            pass

    if see_link is None:
        # Print debug details for troubleshooting
        cur_url = sb.get_current_url()
        title = sb.get_title() or ""
        print(f"❌ 'See' link not found")
        print(f"Current URL: {cur_url}")
        print(f"Page Title: {title}")
        try:
            links = sb.find_elements("a")
            print(f"     Total of {len(links)} links found on page:")
            for a in links[:20]:
                href = a.get_attribute("href") or ""
                txt  = (a.text or "").strip()[:30]
                if href:
                    print(f"       - [{txt}] -> {href}")
        except Exception:
            pass
        sb.save_screenshot("servers_page_fail.png")
        return False

    print("🖱️  Clicking 'See' to navigate to server details...")
    see_link.click()
    time.sleep(5)
    print(f"📄 Current page: {sb.get_current_url()}")
    return True


def _open_renew_modal(sb) -> bool:
    """Scrolls to the Renew button and clicks it to open modal"""
    print("\n🔄 Locating Renew button...")
    try:
        renew_btn = sb.find_element('button[data-bs-target="#renew-modal"]', timeout=10)
    except Exception:
        try:
            renew_btn = sb.find_element('button.btn.btn-outline-primary', timeout=5)
        except Exception:
            print("  ❌ Renew button not found")
            return False

    sb.execute_script("""
        (function(){
            var btn = document.querySelector('button[data-bs-target="#renew-modal"]')
                     || document.querySelector('button.btn.btn-outline-primary');
            if (btn) btn.scrollIntoView({behavior:'smooth',block:'center'});
        })()
    """)
    time.sleep(0.8)
    renew_btn.click()
    print("🖱️ Renew button clicked, waiting for modal...")
    time.sleep(3)

    try:
        sb.find_element('div.modal.show', timeout=5)
        print("✅ Renew modal popped up")
        return True
    except Exception:
        print("⚠️ Modal did not appear")
        return False


# def _solve_altcha(sb) -> bool:
#     """Handle ALTCHA Captcha"""
#     print("\n🔐 Handling ALTCHA Captcha...")
#     time.sleep(2)
#
#     # Check if already automatically passed
#     if sb.execute_script(_ALTCHA_SOLVED_JS):
#         print("✅ ALTCHA already automatically passed")
#         return True
#
#     # Expand iframe inside modal and fetch coordinates
#     coords = None
#     try:
#         coords = sb.execute_script(_ALTCHA_EXPAND_JS)
#     except Exception:
#         pass
#
#     if coords:
#         print(f"  📍 Found modal iframe coordinates: ({coords['cx']}, {coords['cy']})")
#
#     # Try up to 3 rounds
#     for attempt in range(3):
#         if sb.execute_script(_ALTCHA_SOLVED_JS):
#             print(f"✅ ALTCHA passed (Round {attempt + 1})")
#             return True
#
#         # Strategy 1: xdotool physical click on iframe coordinates
#         if coords:
#             try:
#                 wi = sb.execute_script(_WININFO_JS)
#             except Exception:
#                 wi = {"sx": 0, "sy": 0, "oh": 800, "ih": 768}
#             bar = wi["oh"] - wi["ih"]
#             ax  = coords["cx"] + wi["sx"]
#             ay  = coords["cy"] + wi["sy"] + bar
#             print(f"🖱️  ALTCHA clicking checkbox ({ax}, {ay})")
#             _xdotool_click(ax, ay)
#
#         # Strategy 2: SeleniumBase native click on modal iframe element
#         try:
#             iframes = sb.find_elements('div.modal.show iframe')
#             for iframe in iframes:
#                 try:
#                     iframe.click()
#                     print("🖱️  SeleniumBase clicked modal iframe")
#                 except Exception:
#                     pass
#         except Exception:
#             pass
#
#         # Strategy 3: JS loop through all clickable elements inside modal
#         sb.execute_script("""
#             (function(){
#                 var modal = document.querySelector('div.modal.show');
#                 if (!modal) return;
#                 // Click iframe
#                 var iframes = modal.querySelectorAll('iframe');
#                 for (var i = 0; i < iframes.length; i++) {
#                     iframes[i].click();
#                     iframes[i].dispatchEvent(new MouseEvent('click', {bubbles:true}));
#                 }
#                 // Click labels with checkbox
#                 var labels = modal.querySelectorAll('label');
#                 for (var j = 0; j < labels.length; j++) {
#                     var txt = (labels[j].textContent || '').toLowerCase();
#                     if (txt.includes('robot') || txt.includes('captcha') || txt.includes('verify'))
#                         labels[j].click();
#                 }
#                 // Click checkbox
#                 var cbs = modal.querySelectorAll('input[type="checkbox"]');
#                 for (var k = 0; k < cbs.length; k++) {
#                     if (!cbs[k].disabled) {
#                         cbs[k].click();
#                         cbs[k].dispatchEvent(new MouseEvent('click', {bubbles:true}));
#                     }
#                 }
#             })()
#         """)
#
#         # Wait for verification result
#         for _ in range(6):
#             time.sleep(1)
#             if sb.execute_script(_ALTCHA_SOLVED_JS):
#                 print(f"✅ ALTCHA passed (Round {attempt + 1})")
#                 return True
#
#         print(f"  ⚠️ Round {attempt + 1} did not pass, retrying...")
#         # Re-fetch coordinates (iframe might have re-rendered)
#         try:
#             new_coords = sb.execute_script(_ALTCHA_EXPAND_JS)
#             if new_coords:
#                 coords = new_coords
#         except Exception:
#             pass
#
#     print("  ❌ ALTCHA failed after 3 rounds")
#     return False


def _submit_renew(sb):
    """Clicks the Renew submission button inside the modal"""
    print("🖱️  Clicking the Renew button in modal...")
    try:
        submit = sb.find_element('div.modal-footer button.btn.btn-primary', timeout=10)
        submit.click()
    except Exception:
        sb.execute_script("""
            (function(){
                var m = document.querySelector('button.btn.btn-primary');
                if (!m) return;
                var bs = m.querySelectorAll('button');
                for (var i = 0; i < bs.length; i++)
                    if (/renew/i.test(bs[i].textContent)) bs[i].click();
            })()
        """)
    time.sleep(8)


def _check_renew_result(sb):
    """Reads alert notices to determine renewal outcome and push TG notification"""
    print("\n📋 Checking renewal result...")
    alert_text = _read_alert(sb)
    if not alert_text:
        time.sleep(3)
        alert_text = _read_alert(sb)

    if alert_text:
        print(f"📩 Page alert: {alert_text}")
        low = alert_text.lower()
        if "can't renew" in low or "unable" in low:
            send_tg_message("⏳", "Not renewal time yet", alert_text)
        elif any(kw in low for kw in ("renewed", "success", "extended")):
            send_tg_message("✅", "Renewal successful", alert_text)
        else:
            send_tg_message("ℹ️", "Renewal action executed", alert_text)
    else:
        print("ℹ️ No clear alert prompt detected, renewal action may not have taken effect")
        send_tg_message("ℹ️", "Renewal action executed", "No clear prompt detected")


def renew_server(sb):
    """Called after successful login: navigate to details -> Renew -> ALTCHA -> Submit"""
    print("\n" + "#" * 25)
    print("  Starting auto-renewal flow")
    print("#" * 25)

    if not _goto_server_detail(sb):
        return

    if not _open_renew_modal(sb):
        return

    # altcha_ok = _solve_altcha(sb)
    # if not altcha_ok:
    #     print("⚠️ ALTCHA verification not passed, still attempting to submit Renew...")

    _submit_renew(sb)
    _check_renew_result(sb)


# Script Execution Entry Point (Optional Proxy)
def main():
    print("#" * 25)
    print("   Katabump Auto-Login & Renewal")
    print("#" * 25)

    IS_PROXY = os.environ.get("IS_PROXY", "false").lower() == "true"
    proxy_str = os.environ.get("PROXY_SERVER", "").strip() or "http://127.0.0.1:1081"
    sb_kwargs = {"uc": True, "headless": False}

    if IS_PROXY:
        print(f"🔗 Using proxy: {proxy_str}")
        sb_kwargs["proxy"] = proxy_str
    else:
        print("🌐 No proxy used, direct connection")
    
    print("🚀 Launching browser...")
    with SB(**sb_kwargs) as sb:
        # print("✅ Browser launched")
        try:
            sb.open("https://api.ip.sb/ip")
            print(f"📍  Current outbound IP: {sb.get_text('body')}")
        except Exception:
            pass

        if login(sb):
            renew_server(sb)   # Auto-renew after successful login
        else:
            print("\n❌ Login failed, aborting subsequent renewal flow.")
            send_tg_message("❌", "Login failed", "Unknown")

if __name__ == "__main__":
    main()
