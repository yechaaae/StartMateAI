package com.kakao.backend.startupProfile.controller;

import com.kakao.backend.auth.service.AuthException;
import com.kakao.backend.auth.service.AuthSession;
import com.kakao.backend.startupProfile.dto.StartupProfileRequest;
import com.kakao.backend.startupProfile.dto.StartupProfileResponse;
import com.kakao.backend.startupProfile.dto.StartupProfileStatusResponse;
import com.kakao.backend.startupProfile.service.StartupProfileService;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/profile")
@RequiredArgsConstructor
// 로그인한 사용자의 창업 프로필 상태 조회와 온보딩 저장 API를 담당합니다.
public class StartupProfileController {

    private final StartupProfileService startupProfileService;

    // 프론트가 온보딩 페이지로 이동해야 하는지 판단할 수 있는 상태를 반환합니다.
    @GetMapping("/status")
    public StartupProfileStatusResponse status(HttpSession session) {
        return startupProfileService.getStatus(getLoginUserId(session));
    }

    // 저장된 창업 프로필 상세 정보를 반환합니다.
    @GetMapping
    public StartupProfileResponse getProfile(HttpSession session) {
        return startupProfileService.getProfile(getLoginUserId(session));
    }

    // 온보딩에서 입력한 창업 프로필을 생성하거나 갱신합니다.
    @PostMapping
    public StartupProfileResponse saveProfile(
            @RequestBody StartupProfileRequest request,
            HttpSession session
    ) {
        return startupProfileService.saveProfile(getLoginUserId(session), request);
    }

    private Long getLoginUserId(HttpSession session) {
        Object userId = session.getAttribute(AuthSession.LOGIN_USER_ID);
        if (!(userId instanceof Long id)) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return id;
    }
}
