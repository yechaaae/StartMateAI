package com.kakao.backend.workspace.presentation;

import com.kakao.backend.common.presentation.LoginUserSessionResolver;
import com.kakao.backend.workspace.application.SavedResultService;
import com.kakao.backend.workspace.dto.SaveSavedResultRequest;
import com.kakao.backend.workspace.dto.SavedResultDetailResponse;
import com.kakao.backend.workspace.dto.SavedResultListResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/saved-results")
public class SavedResultController {

    private final SavedResultService savedResultService;
    private final LoginUserSessionResolver loginUserSessionResolver;

    public SavedResultController(
            SavedResultService savedResultService,
            LoginUserSessionResolver loginUserSessionResolver
    ) {
        this.savedResultService = savedResultService;
        this.loginUserSessionResolver = loginUserSessionResolver;
    }

    @GetMapping
    public SavedResultListResponse getSavedResults(HttpSession session) {
        Long userId = loginUserSessionResolver.resolve(session);
        return new SavedResultListResponse(savedResultService.getSavedResults(userId));
    }

    @GetMapping("/latest")
    public ResponseEntity<SavedResultDetailResponse> getLatestResult(
            @RequestParam String sourceFeature,
            HttpSession session
    ) {
        Long userId = loginUserSessionResolver.resolve(session);
        return savedResultService.getLatestResult(userId, sourceFeature)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.noContent().build());
    }

    @GetMapping("/{savedResultId}")
    public SavedResultDetailResponse getSavedResult(
            @PathVariable Long savedResultId,
            HttpSession session
    ) {
        Long userId = loginUserSessionResolver.resolve(session);
        return savedResultService.getSavedResult(userId, savedResultId);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SavedResultDetailResponse saveResult(
            @RequestBody SaveSavedResultRequest request,
            HttpSession session
    ) {
        Long userId = loginUserSessionResolver.resolve(session);
        return savedResultService.save(userId, request);
    }
}
