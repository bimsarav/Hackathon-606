package com.esmhub.notification.service.notification;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import com.esmhub.notification.service.notification.NotificationDtos.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class NotificationController {
    private final NotificationService service;

    public NotificationController(NotificationService service) { this.service = service; }

    @GetMapping("/notifications")
    public PageResponse<NotificationView> mine(CurrentUser me, @RequestParam(defaultValue = "false") boolean unread,
                                               @RequestParam(defaultValue = "1") int page,
                                               @RequestParam(defaultValue = "20") int size) {
        return service.mine(me, unread, page, size);
    }

    @GetMapping("/notifications/unread-count")
    public UnreadCount unreadCount(CurrentUser me) { return service.unreadCount(me); }

    @PostMapping("/notifications/{id}/read") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void read(CurrentUser me, @PathVariable long id) { service.markRead(me, id); }

    @PostMapping("/notifications/read-all") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void readAll(CurrentUser me) { service.markAllRead(me); }

    @GetMapping("/admin/notifications")
    public PageResponse<AdminNotificationView> admin(CurrentUser me, @RequestParam(required = false) String status,
                                                     @RequestParam(defaultValue = "1") int page,
                                                     @RequestParam(defaultValue = "20") int size) {
        return service.adminList(me, status, page, size);
    }

    @PostMapping("/admin/notifications/{id}/retry")
    public AdminNotificationView retry(CurrentUser me, @PathVariable long id) { return service.retry(me, id); }
}
