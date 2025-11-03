## Kịch bản sử dụng điển hình

### Trường hợp 1: Thành công
```
Client: "đi thẳng 2m rẽ phải"
Server: "Bắt đầu thực hiện 2 actions"
Server: "Action 1/2 hoàn thành" (đi thẳng 2m ok)
Server: "Action 2/2 hoàn thành" (rẽ phải ok)
Server: "Hoàn thành tất cả 2 actions"
```

### Trường hợp 2: Gặp vật cản
```
Client: "đi thẳng 5m rẽ trái tiếp 3m"
Server: "Bắt đầu thực hiện 3 actions"
Server: "Action 1/3 hoàn thành" (đi thẳng 5m ok)
Robot: Gặp vật cản khi rẽ trái
Server: "Robot gặp lỗi: Gặp vật cản phía trước, đã dừng lại"
Server: "Đã hủy toàn bộ actions"
```

### Trường hợp 3: Lệnh mới thay thế lệnh cũ
```
Client: "đi thẳng 10m"
Server: "Bắt đầu thực hiện..."
Client: "dừng lại" (lệnh mới)
Server: "Đã hủy lệnh trước đó để thực hiện lệnh mới"
Server: "Bắt đầu thực hiện 1 action mới"