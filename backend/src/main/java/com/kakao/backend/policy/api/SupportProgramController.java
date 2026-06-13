package com.kakao.backend.policy.api;

import com.kakao.backend.policy.dto.RecommendedProgramResponse;
import com.kakao.backend.policy.dto.SupportProgramRecommendationRequest;
import com.kakao.backend.policy.dto.SupportProgramSyncResponse;
import com.kakao.backend.policy.service.SupportProgramService;
import java.util.List;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/support-programs")
public class SupportProgramController {

    private final SupportProgramService supportProgramService;

    public SupportProgramController(SupportProgramService supportProgramService) {
        this.supportProgramService = supportProgramService;
    }

    @PostMapping("/sync")
    public SupportProgramSyncResponse sync(@RequestParam(defaultValue = "all") String source) {
        return supportProgramService.sync(source);
    }

    @PostMapping("/recommend")
    public List<RecommendedProgramResponse> recommend(@RequestBody SupportProgramRecommendationRequest request) {
        return supportProgramService.recommend(request);
    }
}
