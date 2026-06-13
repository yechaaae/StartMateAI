package com.kakao.backend.workspace.dto;

// 새 워크스페이스 생성 요청 (title 미지정 시 기본 이름 사용).
public record CreateWorkspaceRequest(
        String title
) {
}
