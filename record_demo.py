"""
AtlasMind - Automated Executive Demo Recording Script
Runs the complete end-to-end demo flow using Playwright & Google Chrome,
recording high-definition video and converting to MP4 format.

Usage:
    python record_demo.py
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def convert_webm_to_mp4(webm_path: str, mp4_path: str) -> bool:
    """Convert WebM to MP4 using OpenCV if available."""
    try:
        import cv2
        print(f"\n[Video Converter] Converting '{webm_path}' -> '{mp4_path}'...")
        cap = cv2.VideoCapture(webm_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        
        out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_count += 1
            
        cap.release()
        out.release()
        
        if Path(mp4_path).exists() and Path(mp4_path).stat().st_size > 1000:
            size_mb = Path(mp4_path).stat().st_size / (1024 * 1024)
            print(f"[Video Converter] Success! Generated '{mp4_path}' ({size_mb:.2f} MB, {frame_count} frames)")
            return True
    except Exception as e:
        print(f"[Video Converter] OpenCV conversion error: {e}")
    return False

def run_demo():
    rec_dir = Path("recordings")
    rec_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 65)
    print("  ATLASMIND - AUTOMATED DEMO RECORDING (A TO Z)")
    print("=" * 65)
    print("[1/5] Launching Chrome browser with video recording enabled...")
    
    with sync_playwright() as p:
        # Launch using installed system Chrome for 100% native fidelity
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(
            record_video_dir=str(rec_dir),
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        # 1. Open App
        print("[2/5] Navigating to http://localhost:8501...")
        page.goto("http://localhost:8501", timeout=60000)
        page.wait_for_timeout(3500)
        
        # Reset conversation if already active
        reset_btn = page.locator("button:has-text('Start New Conversation')")
        if reset_btn.count() > 0:
            print("  -> Resetting to clean conversation state...")
            reset_btn.first.click()
            page.wait_for_timeout(2000)
            
        # 2. Select General Employee role
        print("  -> Setting role persona to 'General Employee'...")
        role_select = page.locator("[data-testid='stSelectbox']").first
        role_select.click()
        page.wait_for_timeout(600)
        gen_opt = page.locator("li[role='option']:has-text('General Employee')")
        if gen_opt.count() > 0:
            gen_opt.first.click()
        page.wait_for_timeout(2000)
        
        # Helper function to submit chat query
        def ask_question(prompt_text: str, description: str, pause_sec: float = 4.0):
            print(f"\n[Demo Action] {description}")
            print(f"  Question: \"{prompt_text}\"")
            textarea = page.locator("textarea").first
            textarea.click()
            textarea.fill(prompt_text)
            page.wait_for_timeout(400)
            textarea.press("Enter")
            
            # Wait for response to generate
            page.wait_for_timeout(2500)
            # Wait until Streamlit status indicators finish
            page.wait_for_timeout(pause_sec * 1000)
            print("  -> Response rendered and displayed.")

        # 3. Query 1: Annual Leave (English)
        ask_question(
            prompt_text="What is the annual leave entitlement at Atlas Honda?",
            description="Query 1: Asking Annual Leave entitlement (English)",
            pause_sec=4.0
        )
        
        # 4. Query 2: Casual Leave (Roman Urdu)
        ask_question(
            prompt_text="Casual leave kitni milti hai?",
            description="Query 2: Asking Casual Leave rules (Roman Urdu auto-detection)",
            pause_sec=4.0
        )
        
        # 5. Query 3: Press Shop PPE Mandate
        ask_question(
            prompt_text="Press shop me kon sa PPE pehnna zaroori hai?",
            description="Query 3: Asking Press Shop factory safety PPE requirements",
            pause_sec=4.0
        )
        
        # 6. Switch Role to Executive & Compliance Admin
        print("\n[Demo Action] Switching role to 'Executive & Compliance Admin'...")
        role_select = page.locator("[data-testid='stSelectbox']").first
        role_select.click()
        page.wait_for_timeout(600)
        admin_opt = page.locator("li[role='option']:has-text('Executive & Compliance Admin')")
        if admin_opt.count() > 0:
            admin_opt.first.click()
        page.wait_for_timeout(2500)
        
        # 7. Enter Admin PIN
        print("[Demo Action] Entering Admin PIN 'atlas123' to unlock governance controls...")
        pin_inputs = page.locator("input[type='password']")
        if pin_inputs.count() > 0:
            pin_inputs.first.fill("atlas123")
            page.wait_for_timeout(500)
            unlock_btn = page.locator("button:has-text('Unlock')").first
            if unlock_btn.count() > 0:
                unlock_btn.click()
            else:
                pin_inputs.first.press("Enter")
        page.wait_for_timeout(2500)
        
        # 8. Open Document Hub & walkthrough tabs
        print("\n[Demo Action] Opening Document Hub...")
        doc_hub_tab = page.locator("button[data-baseweb='tab']:has-text('Document Hub')")
        if doc_hub_tab.count() > 0:
            doc_hub_tab.first.click()
            page.wait_for_timeout(2000)
            
            # Subtab 1: Upload Policy
            print("  -> Showing 'Upload Policy' tab...")
            up_tab = page.locator("button[data-baseweb='tab']:has-text('Upload')")
            if up_tab.count() > 0:
                up_tab.first.click()
                page.wait_for_timeout(2500)
                
            # Subtab 2: Edit Policy
            print("  -> Showing 'Edit Policy' tab...")
            edit_tab = page.locator("button[data-baseweb='tab']:has-text('Edit')")
            if edit_tab.count() > 0:
                edit_tab.first.click()
                page.wait_for_timeout(2500)
                
            # Subtab 3: Delete Policy
            print("  -> Showing 'Delete Policy' tab...")
            del_tab = page.locator("button[data-baseweb='tab']:has-text('Delete')")
            if del_tab.count() > 0:
                del_tab.first.click()
                page.wait_for_timeout(2500)
                
            # Subtab 4: Document Inventory
            print("  -> Showing 'Document Inventory' tab...")
            inv_tab = page.locator("button[data-baseweb='tab']:has-text('Inventory')")
            if inv_tab.count() > 0:
                inv_tab.first.click()
                page.wait_for_timeout(2500)
                
        # 9. Return to main chat screen
        print("\n[Demo Action] Navigating back to main Knowledge Assistant tab...")
        chat_tab = page.locator("button[data-baseweb='tab']:has-text('Knowledge Assistant')")
        if chat_tab.count() > 0:
            chat_tab.first.click()
            page.wait_for_timeout(3500)
            
        print("\n[4/5] Demo flow completed. Finalizing video recording...")
        context.close()
        browser.close()
        
    # Find generated webm video
    webm_files = sorted(rec_dir.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)
    if webm_files:
        latest_webm = webm_files[0]
        mp4_dest = rec_dir / "atlasmind_demo.mp4"
        converted = convert_webm_to_mp4(str(latest_webm), str(mp4_dest))
        
        final_video = mp4_dest if converted else latest_webm
        size_mb = final_video.stat().st_size / (1024 * 1024)
        
        print("\n" + "=" * 65)
        print("  [SUCCESS] DEMO RECORDING SAVED SUCCESSFULLY!")
        print("=" * 65)
        print(f"  File Path: {final_video.resolve()}")
        print(f"  Format:    {final_video.suffix.upper()}")
        print(f"  Size:      {size_mb:.2f} MB")
        print("=" * 65)
        return str(final_video.resolve())
    else:
        print("[Error] No video file was generated.")
        return None

if __name__ == "__main__":
    run_demo()
