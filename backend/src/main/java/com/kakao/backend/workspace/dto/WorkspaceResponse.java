package com.kakao.backend.workspace.dto;

import com.kakao.backend.workspace.domain.Workspace;
import org.springframework.web.util.HtmlUtils;

// 사용자의 워크스페이스 정보를 프론트에서 사용할 수 있는 형태로 전달합니다.
public record WorkspaceResponse(
        Long id,
        String title,
        String status,
        String selectedIdeaTitle,
        String selectedIdeaCategory,
        Integer selectedIdeaScore,
        String selectedIdeaReason
) {

    public static WorkspaceResponse from(Workspace workspace) {
        return new WorkspaceResponse(
                workspace.getId(),
                escape(workspace.getTitle()),
                workspace.getStatus(),
                escape(workspace.getSelectedIdeaTitle()),
                escape(workspace.getSelectedIdeaCategory()),
                workspace.getSelectedIdeaScore(),
                escape(workspace.getSelectedIdeaReason()));
    }

    private static String escape(String value) {
        return value == null ? null : HtmlUtils.htmlEscape(value);
    }
}
