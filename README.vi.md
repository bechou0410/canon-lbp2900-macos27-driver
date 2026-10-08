# Canon LBP2900 cho macOS 27

[English](README.md) · **Tiếng Việt**

Bộ driver USB đầy đủ dành cho **Canon LBP2900 / LBP2900B**, tích hợp Canon Printer Utility, Print Center của macOS và các tùy chọn in Canon gốc. Cài trực tiếp, không cần cài thêm bộ driver Canon riêng.

**[Tải Canon LBP2900 v27.3.3](https://github.com/bechou0410/canon-lbp2900-macos27-driver/releases/download/v27.3.3/Canon-LBP2900-v27.3.3.pkg)** · [Ghi chú phát hành và checksum](https://github.com/bechou0410/canon-lbp2900-macos27-driver/releases/tag/v27.3.3)

Một bộ cài chứa tiếng Anh và tiếng Việt, tự chọn theo ngôn ngữ ưu tiên của macOS; tiếng Anh là ngôn ngữ dự phòng. Utility và hộp thoại in Canon gốc vẫn dùng tiếng Anh.

## Driver hoạt động thực tế

<table>
<tr><th width="25%">Bộ cài</th><th width="25%">Sẵn sàng in</th><th width="25%">Cảnh báo mở nắp</th><th width="25%">Cảnh báo hết giấy</th></tr>
<tr><td><a href="docs/images/installer-preview.png"><img src="docs/images/installer-preview.png" alt="Bộ cài" width="100%"></a></td><td><a href="docs/images/utility-ready.png"><img src="docs/images/utility-ready.png" alt="Sẵn sàng in" width="100%"></a></td><td><a href="docs/images/utility-cover-open.png"><img src="docs/images/utility-cover-open.png" alt="Cảnh báo mở nắp" width="100%"></a></td><td><a href="docs/images/utility-out-of-paper.png"><img src="docs/images/utility-out-of-paper.png" alt="Cảnh báo hết giấy" width="100%"></a></td></tr>
</table>

Ảnh người dùng cung cấp từ driver đã cài: bộ cài, sẵn sàng in, nhận diện mở nắp và cảnh báo hết giấy. Bấm ảnh để xem kích thước đầy đủ. Ảnh bộ cài hiển thị v27.3.1; v27.3.3 bổ sung sửa lỗi dịch vụ nền crash khi hủy job đang lỗi.

## Tính năng và kiểm chứng

| Tính năng | Trạng thái |
|---|---|
| In USB | Đã kiểm trên LBP2900, Apple Silicon và macOS 27.2; sáu tờ in được người dùng xác nhận trong quá trình nghiệm thu driver. |
| Trạng thái máy in | Đã kiểm sẵn sàng, hết giấy, mở nắp và rút/cắm lại USB. |
| Điều khiển job | Pause/Resume đã kiểm. v27.3.3 sửa lỗi Cancel mới tái hiện khi hết giấy; kiểm thử hồi quy đạt và người dùng đã xác nhận thử lại thành công với khay trống trên LBP2900/macOS 27.2. |
| Print Center của macOS | Đã kiểm điều khiển queue và mở Printer Utility. |
| Tùy chọn Canon | Các mục Finishing, Paper Source, Quality/Toner và About mở đúng. |
| Runtime riêng | Hoạt động tách biệt với Canon gốc; cài lại Canon chính thức đã giữ driver riêng và in được một trang thực tế. |
| Cài đè / nâng cấp | Cài đè lên v27.3.3 trên máy thật giữ nguyên PPD của hai máy in và trạng thái máy in mặc định. Kiểm thử payload tự động đạt cho cài lại cùng bản và nâng cấp bản cũ. |

**Phạm vi thử:** LBP2900 / Apple Silicon / macOS 27.2. Đây là bản thử nghiệm; phần cứng LBP2900B/Intel, máy Mac/macOS khác, phục hồi sau reboot/đăng nhập, Cleaning, mọi tùy chọn giấy/chất lượng và độ ổn định dài hạn còn cần kiểm chứng. Số phiên bản là phiên bản driver. Xem [bằng chứng kiểm thử](docs/verification.md).

## Cài đặt

1. Hoàn tất hoặc hủy mọi job trong Canon Printer Utility.
2. Bật một LBP2900, cắm USB và mở PKG. Có thể cài đè bản driver dự án còn nguyên vẹn mà không cần gỡ trước.
3. Làm theo Installer và xác thực trên Mac. Khi cài mới, gói tự tạo **Canon LBP2900** cùng kết nối và dịch vụ trạng thái. Khi cài đè, queue của dự án, tùy chọn và máy in mặc định được giữ lại.
4. Mở **System Settings → Printers & Scanners → Canon LBP2900 → Options & Supplies → Utility → Open Printer Utility**. Kiểm tra trạng thái **Ready to Print**.

Bản phát hành này được ký bằng Developer ID Installer, Apple notarize và đã xác thực ticket stapled. Nếu macOS vẫn báo không thể xác minh bộ cài, hãy đối chiếu SHA-256 với checksum của bản phát hành rồi tải lại từ release chính thức. Nếu cảnh báo còn xuất hiện, đừng cài hoặc bỏ qua Gatekeeper; hãy gửi lại nội dung cảnh báo và phiên bản macOS.

Nếu chưa cắm máy in lúc cài, kết nối USB rồi chạy:

```sh
sudo '/Library/Application Support/CanonLBP2900Standalone/lbp2900-standalone' configure-connected
```

Queue tạo thủ công trước đó được giữ lại để kiểm tra; chỉ thêm queue USB trong macOS chưa thiết lập kết nối trạng thái gốc. Hoàn tất job và chỉ xóa queue Canon bị trùng trước khi chạy lại thiết lập. Nếu cắm nhiều máy, cần chọn thủ công. Xem [thiết lập và khôi phục](docs/standalone-capt.md).

## Cài lại hoặc gỡ

Để cài lại hoặc nâng cấp, mở PKG mới sau khi hoàn tất mọi job Canon. File bị sửa hoặc không rõ nguồn gốc sẽ bị từ chối. Nếu cài bị gián đoạn, chạy lại PKG; chỉ phục hồi khi integrity của bản đang có đạt.

Để gỡ, hoàn tất/hủy mọi job Canon và xóa queue của driver trong Printers & Scanners, rồi chạy:

```sh
sudo '/Library/Application Support/CanonLBP2900Standalone/lbp2900-standalone' remove
```

Helper gỡ runtime và receipt thuộc dự án. Driver Canon gốc, máy in khác và tùy chọn cá nhân được giữ nguyên.

## Build

Trên macOS có Python 3.11+ và command-line tools của Apple:

```sh
python3 tools/capt-standalone.py
python3 tests/standalone-test.py
```

Builder xác minh nguồn Canon chính thức, đóng gói thành phần cần thiết và tạo một PKG song ngữ cùng file SHA-256 trong `artifacts/`. Kiểm thử dùng payload thật và dựng tài liệu, không in giấy. [Chi tiết build và kiến trúc](docs/standalone-capt.md).

## Ghi nhận

Phát triển với sự hỗ trợ của **OpenAI Codex** trong lập trình, gỡ lỗi, kiểm thử tự động và viết tài liệu; người duy trì dự án thực hiện thử nghiệm phần cứng và xác nhận bản in thực tế.

Dựa trên Canon Printer Driver & Utilities for Mac V10.0.10. Canon sở hữu mã gốc và tài nguyên; giấy phép gốc được giữ trong bộ cài. Đây là dự án cộng đồng độc lập, không được Canon hoặc Apple bảo trợ/chứng nhận. [Thông báo bản quyền](NOTICE.md) · [Nguồn Canon chính thức](https://vn.canon/en/support/0101321320) · [Các bản phát hành trước](https://github.com/bechou0410/canon-lbp2900-macos27-driver/releases).
