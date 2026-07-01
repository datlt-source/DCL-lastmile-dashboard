import os
import time
import json
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.getenv("GHN_PROFILE_DIR", "./bot_profile_backlog_test")
GHN_BASE_URL = os.getenv("GHN_BASE_URL", "https://nhanh.ghn.vn")

# Nếu bạn có web test riêng, export GHN_BASE_URL trước khi chạy.
# Ví dụ: export GHN_BASE_URL=https://test.nhanh.ghn.vn

def safe_int(value):
    try:
        return int(str(value).replace(',', '').strip())
    except Exception:
        return 0


def calculate_totals(stats):
    total = 0
    target_labels = ["Giao", "Ưu tiên giao", "Trả"]
    for label, values in stats.items():
        if any(target.lower() in label.lower() for target in target_labels):
            for val in values:
                total += safe_int(val)
    return total


def extract_range_values(values):
    nums = [safe_int(val) for val in values]
    if len(nums) >= 4:
        return nums[1], nums[2]
    if len(nums) == 3:
        return nums[0], nums[1]
    if len(nums) == 2:
        return nums[0], nums[1]
    return 0, 0


def extract_backlog_details(stats):
    details = {
        "Giao_120_192": 0,
        "Giao_192_plus": 0,
        "Uu_tien_giao_120_192": 0,
        "Uu_tien_giao_192_plus": 0,
        "Tra_120_192": 0,
        "Tra_192_plus": 0,
    }

    for label, values in stats.items():
        label_lower = label.lower()
        if "ưu tiên giao" in label_lower or "uu tien" in label_lower:
            r120, r192 = extract_range_values(values)
            details["Uu_tien_giao_120_192"] = r120
            details["Uu_tien_giao_192_plus"] = r192
        elif "trả" in label_lower:
            r120, r192 = extract_range_values(values)
            details["Tra_120_192"] = r120
            details["Tra_192_plus"] = r192
        elif "giao" in label_lower:
            r120, r192 = extract_range_values(values)
            details["Giao_120_192"] = r120
            details["Giao_192_plus"] = r192

    return details

def scrape_backlog_data(page, loc_code, loc_name):
    # 1. Xóa bưu cục cũ
    page.evaluate("document.querySelectorAll('.ant-select-selection-item-remove').forEach(el => el.click())")
    time.sleep(0.5)
    
    # 2. Nhập bưu cục mới
    page.evaluate(f"""
        (locCode) => {{
            const inputs = document.querySelectorAll('input.ant-select-selection-search-input');
            if (inputs.length >= 2) {{
                const targetInput = inputs[1];
                targetInput.focus();
                targetInput.value = locCode;
                targetInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }}
    """, loc_code)
    
    time.sleep(1)
    page.keyboard.press("Enter")
    time.sleep(1.5)
    
    dropdown_item = page.locator(f".ant-select-item-option-content:has-text('{loc_name}')")
    if dropdown_item.count() > 0:
        dropdown_item.first.click()
    
    page.locator("button:has-text('Cập nhật dữ liệu')").click()
    
    page.wait_for_selector(".ant-table-row", timeout=15000)
    time.sleep(1)
    
    stats = page.evaluate("""() => {
        const rows = document.querySelectorAll('.ant-table-row');
        let data = {};
        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
            if (cells.length > 0) { data[cells[0]] = cells.slice(1); }
        });
        return data;
    }""")
    total = calculate_totals(stats)
    details = extract_backlog_details(stats)
    result = {"total_sum": total}
    result.update(details)
    return result

def run_isolated_test():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome")
        page = context.pages[0]
        page.goto(f"{GHN_BASE_URL}/lastmile/report/backlog-lgt")
        
        print("🚀 Đã mở trình duyệt. Hãy đăng nhập và vào trang 'Tồn đọng'.")
        input("Nhấn Enter sau khi đã vào đúng trang để bắt đầu cào...")

        with open("all_buu_cuc.json", "r", encoding="utf-8") as f:
            test_hubs = json.load(f)

        all_results = {}
        for hub in test_hubs:
            loc_name, loc_code = hub['locationName'], hub['locationCode']
            print(f"🔄 Đang cào: {loc_name} ({loc_code})")
            try:
                result = scrape_backlog_data(page, loc_code, loc_name)
                all_results[loc_name] = result
                print(f"✅ Xong {loc_name}. Tổng: {result['total_sum']}")
            except Exception as e:
                all_results[loc_name] = {"total_sum": 0}
                print(f"⚠️ Lỗi {loc_name}: {e}")

        with open("final_backlog_data.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        print("🏁 Đã xong!")
        context.close()

if __name__ == "__main__":
    run_isolated_test()