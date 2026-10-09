# BitLocker Recovery Key Prompt at Startup

## Symptoms
- Workstation boots into blue screen prompting: 'BitLocker - Enter the recovery key for this drive (Keyboard Layout: US)'.
- Screen displays Recovery Key ID (first 8 characters: e.g., `A1B2C3D4-...`).
- Occurs immediately after a motherboard replacement, BIOS/UEFI firmware update, or docking station firmware flash.

## Checks
1. Read the 8-character Key ID displayed on the BitLocker prompt screen.
2. Verify user identity via voice/video or manager approval before providing any recovery key.
3. Access Microsoft Entra ID (Azure AD portal) or Microsoft Endpoint Manager (Intune) admin center:
   `Devices > All devices > [Device Name] > BitLocker keys`.
4. For on-premises Active Directory: open Active Directory Users and Computers > Computer Properties > 'BitLocker Recovery' tab.

## Resolution
- Retrieve the 48-digit numerical recovery key matching the displayed Key ID.
- Input the 48-digit key into the BitLocker prompt and press Enter to boot into Windows.
- Once booted into Windows:
  1. Open Command Prompt (Administrator).
  2. Suspend and resume BitLocker to re-bind TPM PCR measurements to the new BIOS/firmware state:
     ```cmd
     manage-bde -protectors -disable C:
     manage-bde -protectors -enable C:
     ```
  3. Verify TPM status: `manage-bde -status C:`.

## Escalation
If TPM chip is non-responsive or motherboard replacement altered TPM binding permanently, assign to Senior IT Desktop Support to verify drive integrity or restore from corporate cloud backup.

## Hướng dẫn nhanh (Tiếng Việt)
1. Chụp lại màn hình xanh BitLocker, đặc biệt là 8 ký tự đầu của dòng 'Recovery Key ID'.
2. Liên hệ bộ phận IT Helpdesk công ty, cung cấp tên máy tính và Key ID để IT tra cứu mã khóa khôi phục 48 chữ số trong hệ thống quản trị (Intune / Azure AD).
3. Nhập dãy 48 số do IT cấp vào màn hình máy tính để đăng nhập vào Windows.
4. Sau khi vào Windows, mở cmd (Admin) chạy lệnh `manage-bde -protectors -disable C:` rồi `manage-bde -protectors -enable C:` để đồng bộ lại khóa với chip TPM, tránh bị hỏi lại ở lần khởi động sau.

## Source and scope
- Microsoft Learn, [Find your BitLocker recovery key](https://support.microsoft.com/en-us/windows/finding-your-bitlocker-recovery-key-in-windows-6b71f270-4802-5763-5243-73d7fbab4483), accessed 2026-10-06.
