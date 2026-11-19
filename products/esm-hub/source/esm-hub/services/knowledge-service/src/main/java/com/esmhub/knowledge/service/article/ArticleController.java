package com.esmhub.knowledge.service.article;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import com.esmhub.knowledge.service.article.ArticleDtos.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1/kb/articles")
public class ArticleController {
    private final ArticleService service;

    public ArticleController(ArticleService service) { this.service = service; }

    @GetMapping
    public PageResponse<ArticleView> search(CurrentUser me, @RequestParam(required = false) @Size(max = 200) String q,
                                            @RequestParam(required = false) Long categoryId, @RequestParam(required = false) String status,
                                            @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.search(me, q, categoryId, status, page, size);
    }

    @GetMapping("/{id}")
    public ArticleView read(CurrentUser me, @PathVariable long id) { return service.read(me, id); }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ArticleView create(CurrentUser me, @Valid @RequestBody CreateArticle body) { return service.create(me, body); }

    @PatchMapping("/{id}")
    public ArticleView edit(CurrentUser me, @PathVariable long id, @Valid @RequestBody UpdateArticle body) {
        return service.edit(me, id, body);
    }

    @PostMapping("/{id}/status")
    public ArticleView status(CurrentUser me, @PathVariable long id, @Valid @RequestBody ChangeStatus body) {
        return service.changeStatus(me, id, body.status());
    }

    @PostMapping("/{id}/feedback")
    public ArticleView feedback(CurrentUser me, @PathVariable long id, @Valid @RequestBody Feedback body) {
        return service.vote(me, id, body.helpful(), body.comment());
    }
}
