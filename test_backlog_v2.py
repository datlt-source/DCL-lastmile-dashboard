import time
import json
from playwright.sync_api import sync_playwright

def calculate_totals(stats):
    """Tính tổng theo yêu cầu: Giao + Ưu tiên giao + Trả"""
    total = 0
    # Các nhãn cần cộng
    target_labels = ["Giao", "Ưu tiên giao", "Trả"]
    
    for label, values in stats.items():
        # Kiểm tra nếu tên dòng có chứa một trong các từ khóa trên
        if any(target in label for target in target_labels):
            for val in values:
                try:
                    # Loại bỏ dấu phẩy nếu có và cộng vào tổng
                    total += int(val.replace(',', ''))
                except ValueError:
                    continue
    return total

def run_isolated_test():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="./bot_profile",
            headless=False,
            channel="chrome"
        )
        page = context.pages[0]
        page.goto("https://nhanh.ghn.vn/lastmile/report/backlog-lgt")
        
        print("🚀 Đã mở trình duyệt. Hãy đăng nhập và vào trang 'Tồn đọng'.")
        input("Nhấn Enter sau khi đã vào đúng trang để bắt đầu cào...")

        # Đọc file hubs_test.json để test trước 2 bưu cục
        with open("hubs_test.json", "r", encoding="utf-8") as f:
            test_hubs = json.load(f)

        all_results = {}
        for hub in test_hubs:
            print(f"🔄 Đang cào tồn đọng: {hub['name']} ({hub['id']})")
            
            # 1. Xóa bưu cục cũ
            page.evaluate("document.querySelectorAll('.ant-select-selection-item-remove').forEach(el => el.click())")
            time.sleep(0.5)
            
            # 2. Nhập bưu cục vào ô báo cáo (ô thứ 2) bằng JS để tránh lệch click
            page.evaluate(f"""
                (hubId) => {{
                    const inputs = document.querySelectorAll('input.ant-select-selection-search-input');
                    if (inputs.length >= 2) {{
                        const targetInput = inputs[1];
                        targetInput.focus();
                        targetInput.value = hubId;
                        targetInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
            """, hub['id'])
            
            time.sleep(1)
            page.keyboard.press("Enter")
            time.sleep(1.5)
            
            # 3. Chọn từ danh sách dropdown
            dropdown_item = page.locator(f".ant-select-item-option-content:has-text('{hub['name']}')")
            if dropdown_item.count() > 0:
                dropdown_item.first.click()
            
            # 4. Nhấn nút "Cập nhật dữ liệu"
            page.locator("button:has-text('Cập nhật dữ liệu')").click()
            
            # 5. Cào và tự động tính tổng
            try:
                # Chờ hàng dữ liệu xuất hiện
                page.wait_for_selector(".ant-table-row", timeout=15000)
                time.sleep(1)
                
                stats = page.evaluate("""() => {
                    const rows = document.querySelectorAll('.ant-table-row');
                    let data = {};
                    rows.forEach(row => {
                        const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
                        if (cells.length > 0) {
                            data[cells[0]] = cells.slice(1);
                        }
                    });
                    return data;
                }""")
                
                total_sum = calculate_totals(stats)
                all_results[hub['name']] = {
                    "data": stats,
                    "total_sum": total_sum
                }
                print(f"✅ Xong {hub['name']}. Tổng đơn tồn (Giao/Ưu tiên/Trả): {total_sum}")
            except Exception as e:
                all_results[hub['name']] = {"data": {}, "total_sum": 0}
                print(f"⚠️ Bưu cục {hub['name']} không có dữ liệu đơn tồn.")

        # Lưu kết quả tồn đọng ra file tạm
        with open("final_backlog_data.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        print("\n🏁 Đã cào xong tồn đọng! File 'final_backlog_data.json' đã sẵn sàng.")

if __name__ == "__main__":
    run_isolated_test()