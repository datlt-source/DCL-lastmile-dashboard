import time
from playwright.sync_api import sync_playwright

def force_select_and_scrape():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Truy cập báo cáo
        page.goto("https://nhanh.ghn.vn/lastmile/report/backlog-lgt")
        page.wait_for_load_state("networkidle")
        
        # DANH SÁCH BƯU CỤC CẦN CÀO (Test thử 1-2 cái)
        hubs = ["1083"] 

        for hub_id in hubs:
            print(f"🔄 Đang xử lý bưu cục: {hub_id}")
            
            # 1. BƯỚC QUAN TRỌNG: XÓA BƯU CỤC CŨ ĐANG CHẶN
            # Tìm tất cả các nút 'x' (remove) của bưu cục đã chọn
            close_buttons = page.locator(".ant-select-selection-item-remove")
            if close_buttons.count() > 0:
                print("🧹 Tìm thấy bưu cục cũ, đang xóa...")
                for i in range(close_buttons.count()):
                    close_buttons.nth(i).click()
                time.sleep(1)

            # 2. Click vào vùng chứa (Select container) thay vì click trực tiếp vào input bị chặn
            # Class bao ngoài ô select thường là .ant-select-selector
            container = page.locator(".ant-select-selector").first
            container.click()
            time.sleep(0.5)
            
            # 3. Fill trực tiếp vào input bằng cách dùng .press_sequentially (giả lập gõ phím)
            input_box = page.locator("input.ant-select-selection-search-input").first
            input_box.press_sequentially(hub_id, delay=100)
            time.sleep(1)
            input_box.press("Enter")
            time.sleep(2)
            
            # 4. Nhấn Cập nhật
            page.locator("button:has-text('Cập nhật dữ liệu')").click()
            time.sleep(3)
            
            print(f"✅ Đã chọn xong {hub_id}")

if __name__ == "__main__":
    force_select_and_scrape()