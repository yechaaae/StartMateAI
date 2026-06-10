package com.kakao.backend.workspace.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kakao.backend.user.model.User;
import com.kakao.backend.user.repository.UserRepository;
import com.kakao.backend.workspace.domain.SavedResult;
import com.kakao.backend.workspace.domain.Workspace;
import com.kakao.backend.workspace.dto.SaveSavedResultRequest;
import com.kakao.backend.workspace.dto.SavedResultDetailResponse;
import com.kakao.backend.workspace.dto.SavedResultSummaryResponse;
import com.kakao.backend.workspace.infrastructure.SavedResultRepository;
import com.kakao.backend.workspace.infrastructure.WorkspaceRepository;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Set;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class SavedResultService {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    private static final Set<String> ALLOWED_SOURCE_FEATURES = Set.of("SIMULATOR", "OPERATION");

    private final SavedResultRepository savedResultRepository;
    private final WorkspaceRepository workspaceRepository;
    private final UserRepository userRepository;
    private final ObjectMapper objectMapper;

    public SavedResultService(
            SavedResultRepository savedResultRepository,
            WorkspaceRepository workspaceRepository,
            UserRepository userRepository,
            ObjectMapper objectMapper
    ) {
        this.savedResultRepository = savedResultRepository;
        this.workspaceRepository = workspaceRepository;
        this.userRepository = userRepository;
        this.objectMapper = objectMapper;
    }

    public List<SavedResultSummaryResponse> getSavedResults(Long userId) {
        requireUser(userId);
        return savedResultRepository.findByWorkspaceUserIdOrderByCreatedAtDesc(userId).stream()
                .map(this::toSummaryResponse)
                .toList();
    }

    public SavedResultDetailResponse getSavedResult(Long userId, Long savedResultId) {
        requireUser(userId);
        SavedResult savedResult = savedResultRepository.findByIdAndWorkspaceUserId(savedResultId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Saved result not found."));
        return toDetailResponse(savedResult);
    }

    @Transactional
    public SavedResultDetailResponse save(Long userId, SaveSavedResultRequest request) {
        User user = requireUser(userId);
        String sourceFeature = normalizeRequired(request.sourceFeature(), "Source feature is required.").toUpperCase();
        validateSourceFeature(sourceFeature);
        Workspace workspace = workspaceRepository.findFirstByUserIdAndStatusOrderByIdAsc(userId, "ACTIVE")
                .orElseGet(() -> {
                    Workspace created = Workspace.create("Saved results workspace", "ACTIVE");
                    created.setUser(user);
                    return workspaceRepository.save(created);
                });

        SavedResult savedResult = SavedResult.create(
                workspace,
                sourceFeature.toLowerCase(),
                normalizeRequired(request.resultType(), "Result type is required."),
                request.referenceId(),
                normalizeRequired(request.title(), "Title is required."),
                normalizeOptional(request.summary()),
                writePayload(request.payload())
        );

        SavedResult persisted = savedResultRepository.save(savedResult);
        return toDetailResponse(persisted);
    }

    private User requireUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));
    }

    private SavedResultSummaryResponse toSummaryResponse(SavedResult savedResult) {
        return new SavedResultSummaryResponse(
                savedResult.getId(),
                savedResult.getWorkspace() != null ? savedResult.getWorkspace().getId() : null,
                savedResult.getSourceFeature(),
                savedResult.getResultType(),
                savedResult.getReferenceId(),
                savedResult.getTitle(),
                savedResult.getSummary(),
                savedResult.getCreatedAt() != null ? savedResult.getCreatedAt().format(FORMATTER) : null
        );
    }

    private SavedResultDetailResponse toDetailResponse(SavedResult savedResult) {
        return new SavedResultDetailResponse(
                savedResult.getId(),
                savedResult.getWorkspace() != null ? savedResult.getWorkspace().getId() : null,
                savedResult.getSourceFeature(),
                savedResult.getResultType(),
                savedResult.getReferenceId(),
                savedResult.getTitle(),
                savedResult.getSummary(),
                readPayload(savedResult.getPayload()),
                savedResult.getCreatedAt() != null ? savedResult.getCreatedAt().format(FORMATTER) : null
        );
    }

    private String normalizeRequired(String value, String message) {
        if (value == null) {
            throw new IllegalArgumentException(message);
        }

        String normalized = value.trim();
        if (normalized.isBlank()) {
            throw new IllegalArgumentException(message);
        }
        return normalized;
    }

    private String normalizeOptional(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isBlank() ? null : normalized;
    }

    private void validateSourceFeature(String sourceFeature) {
        if (!ALLOWED_SOURCE_FEATURES.contains(sourceFeature)) {
            throw new IllegalArgumentException("Only simulator and operation reports can be saved.");
        }
    }

    private String writePayload(Map<String, Object> payload) {
        if (payload == null || payload.isEmpty()) {
            throw new IllegalArgumentException("Payload is required.");
        }

        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Payload could not be serialized.", exception);
        }
    }

    private Map<String, Object> readPayload(String payload) {
        try {
            return objectMapper.readValue(payload, new TypeReference<>() {
            });
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Saved payload could not be parsed.", exception);
        }
    }
}
