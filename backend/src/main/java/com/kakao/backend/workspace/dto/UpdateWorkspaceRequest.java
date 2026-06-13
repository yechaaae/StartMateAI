package com.kakao.backend.workspace.dto;

// 워크스페이스 이름/확정 아이템 갱신 요청 (확정 시 selectedIdea 포함).
public record UpdateWorkspaceRequest(
        String title,
        SelectedIdeaRequest selectedIdea
) {

    public record SelectedIdeaRequest(
            String title,
            String category,
            Integer score,
            String reason
    ) {
    }
}
