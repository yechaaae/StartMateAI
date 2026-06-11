package com.kakao.backend.operation.presentation;

import com.kakao.backend.common.presentation.LoginUserSessionResolver;
import com.kakao.backend.operation.application.OperationFeedbackService;
import com.kakao.backend.operation.dto.OperationFeedbackRequest;
import com.kakao.backend.operation.dto.OperationFeedbackResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/operation-feedback")
public class OperationFeedbackController {

    private final OperationFeedbackService operationFeedbackService;
    private final LoginUserSessionResolver loginUserSessionResolver;

    public OperationFeedbackController(
            OperationFeedbackService operationFeedbackService,
            LoginUserSessionResolver loginUserSessionResolver
    ) {
        this.operationFeedbackService = operationFeedbackService;
        this.loginUserSessionResolver = loginUserSessionResolver;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OperationFeedbackResponse save(
            @RequestBody OperationFeedbackRequest request,
            HttpSession session
    ) {
        Long userId = loginUserSessionResolver.resolve(session);
        return operationFeedbackService.save(userId, request);
    }
}
