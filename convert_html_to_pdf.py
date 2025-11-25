"""
HTML to PDF Converter - Giữ nguyên layout như trên web
Screenshot từng slide với độ phân giải cao
"""

import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def convert_slides_to_pdf(html_file, output_pdf="output.pdf"):
    """Chuyển HTML sang PDF - SCREENSHOT từng slide với chất lượng cao"""

    html_path = Path(html_file).resolve()

    if not html_path.exists():
        print(f"❌ Không tìm thấy file: {html_file}")
        return False

    print(f"📄 Đang xử lý: {html_file}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Mở page với viewport tạm để detect kích thước slide thực tế
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # Load file HTML
        page.goto(f"file:///{html_path}")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Detect kích thước thực tế của slide
        slide_dimensions = page.evaluate("""() => {
            const selectors = [
                '.slide', '.slides > *', '.carousel-item', 
                '.swiper-slide', '[data-slide]', '.slider-item',
                'section', '.page', '.sheet'
            ];
            
            for (const sel of selectors) {
                const slides = document.querySelectorAll(sel);
                if (slides.length > 1) {
                    const firstSlide = slides[0];
                    const rect = firstSlide.getBoundingClientRect();
                    const computed = window.getComputedStyle(firstSlide);
                    return {
                        width: firstSlide.offsetWidth || 
                            parseInt(computed.width) || 
                            rect.width,
                        height: firstSlide.offsetHeight || 
                            parseInt(computed.height) || 
                            rect.height
                    };
                }
            }
            return {width: 1920, height: 1080};
        }""")

        print(
            "🔍 Kích thước slide phát hiện: "
            + f"{slide_dimensions['width']}x{slide_dimensions['height']}"
        )

        # Đóng page cũ và mở page mới với viewport ĐÚNG kích thước slide
        page.close()
        page = browser.new_page(
            viewport={
                "width": int(slide_dimensions["width"]),
                "height": int(slide_dimensions["height"]),
            },
            device_scale_factor=2,  # Scale x2 để nét
        )

        # Load file HTML
        page.goto(f"file:///{html_path}")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Đếm số slides
        total_slides = page.evaluate("""() => {
            const selectors = [
                '.slide', '.slides > *', '.carousel-item', 
                '.swiper-slide', '[data-slide]', '.slider-item',
                'section', '.page', '.sheet'
            ];
            
            for (const sel of selectors) {
                const slides = document.querySelectorAll(sel);
                if (slides.length > 1) {
                    return slides.length;
                }
            }
            return 1;
        }""")

        print(f"📊 Tổng số slides: {total_slides}")

        # Tạo thư mục tạm
        temp_dir = Path("temp_screenshots")
        temp_dir.mkdir(exist_ok=True)

        screenshots = []

        for i in range(total_slides):
            print(f"📸 Đang chụp slide {i + 1}/{total_slides}...")

            # Ẩn tất cả, chỉ hiện slide hiện tại
            page.evaluate(
                f"""(index) => {{
                const selectors = [
                    '.slide', '.slides > *', '.carousel-item', 
                    '.swiper-slide', '[data-slide]', '.slider-item',
                    'section', '.page', '.sheet'
                ];
                
                let allSlides = [];
                for (const sel of selectors) {{
                    const slides = document.querySelectorAll(sel);
                    if (slides.length > 1) {{
                        allSlides = Array.from(slides);
                        break;
                    }}
                }}
                
                // Ẩn tất cả
                allSlides.forEach((slide, idx) => {{
                    if (idx === index) {{
                        slide.style.display = 'block';
                        slide.style.visibility = 'visible';
                        slide.style.opacity = '1';
                        slide.classList.add('active');
                    }} else {{
                        slide.style.display = 'none';
                        slide.classList.remove('active');
                    }}
                }});
                
                // Ẩn navigation
                const navs = document.querySelectorAll(
                    '.swiper-button-next, .swiper-button-prev, ' +
                    '.swiper-pagination, .navigation, ' +
                    '[class*="nav"], [class*="arrow"], [class*="control"]'
                );
                navs.forEach(nav => nav.style.display = 'none');
                
                window.scrollTo(0, 0);
            }}""",
                i,
            )

            page.wait_for_timeout(500)

            # Screenshot với chất lượng CỰC CAO
            screenshot_path = temp_dir / f"slide_{i:03d}.png"
            page.screenshot(
                path=str(screenshot_path),
                full_page=False,
                type="png",
                scale="device",  # Dùng device scale
            )
            screenshots.append(screenshot_path)

        browser.close()

        # Chuyển screenshots thành PDF
        print("🔄 Đang chuyển thành PDF...")
        images = []
        for img_path in screenshots:
            img = Image.open(img_path)
            # Chuyển sang RGB nếu cần
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        # Lưu thành PDF - GIỮ NGUYÊN kích thước gốc
        if images:
            images[0].save(
                output_pdf,
                save_all=True,
                append_images=images[1:],
                resolution=150.0,  # DPI vừa phải
                quality=95,
                optimize=False,
            )

        # Xóa file tạm
        print("🧹 Đang dọn dẹp...")
        for img_path in screenshots:
            img_path.unlink()
        temp_dir.rmdir()

        print(f"✅ Hoàn thành! File: {output_pdf}")
        print(f"📄 Tổng số trang: {total_slides}")
        return True


if __name__ == "__main__":
    # Cài đặt:
    # pip install playwright Pillow
    # playwright install chromium

    html_file = sys.argv[1] if len(sys.argv) > 1 else "index_aivision.html"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"

    convert_slides_to_pdf(html_file, output_file)

