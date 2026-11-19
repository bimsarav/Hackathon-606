package com.esmhub.knowledge.service.article;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Component;

/** Full-text search (PostgreSQL websearch syntax, ranked). Returns ids and ranks; entities are loaded by the service. */
@Component
public class ArticleSearch {
    public record Hit(long articleId, Double rank) {}
    public record Result(List<Hit> hits, long total) {}

    private static final String TSV = "to_tsvector('english', title || ' ' || body)";
    private final NamedParameterJdbcTemplate jdbc;

    public ArticleSearch(NamedParameterJdbcTemplate jdbc) { this.jdbc = jdbc; }

    /**
     * @param editorView editors, auditors and admins see every status; others see PUBLISHED plus their own drafts
     */
    public Result search(long companyId, long userId, boolean editorView, String q, Long categoryId, List<String> statuses,
                         int offset, int limit) {
        var p = new MapSqlParameterSource("c", companyId).addValue("u", userId).addValue("off", offset).addValue("lim", limit);
        List<String> where = new ArrayList<>(List.of("company_id = :c"));
        boolean ranked = q != null && !q.isBlank();
        if (ranked) { where.add(TSV + " @@ websearch_to_tsquery('english', :q)"); p.addValue("q", q.trim()); }
        if (categoryId != null) { where.add("category_id = :cat"); p.addValue("cat", categoryId); }
        if (!editorView) where.add("(status = 'PUBLISHED' OR author_id = :u)");
        if (statuses != null && !statuses.isEmpty()) { where.add("status IN (:st)"); p.addValue("st", statuses); }
        String w = String.join(" AND ", where);
        String rank = ranked ? "ts_rank(" + TSV + ", websearch_to_tsquery('english', :q))" : "NULL::float8";
        long total = jdbc.queryForObject("SELECT count(*) FROM articles WHERE " + w, p, Long.class);
        List<Hit> hits = jdbc.query("SELECT article_id, " + rank + " AS rank FROM articles WHERE " + w
                        + " ORDER BY " + (ranked ? "rank DESC, " : "") + "helpful_count DESC, article_id LIMIT :lim OFFSET :off", p,
                (rs, i) -> new Hit(rs.getLong("article_id"), rs.getObject("rank") == null ? null : rs.getDouble("rank")));
        return new Result(hits, total);
    }
}
