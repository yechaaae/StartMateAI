package com.kakao.backend.domain;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.Map;
import org.junit.jupiter.api.Test;

class EntityMappingTests {

    @Test
    void coreEntitiesUseExpectedTableNames() {
        Map<Class<?>, String> tables = Map.ofEntries(
                Map.entry(User.class, "users"),
                Map.entry(StartupProfile.class, "startup_profile"),
                Map.entry(Workspace.class, "workspace"),
                Map.entry(Agent.class, "agent"),
                Map.entry(ChatRoom.class, "chat_room"),
                Map.entry(ChatMessage.class, "chat_message"),
                Map.entry(ChatAgentParticipant.class, "chat_agent_participant"),
                Map.entry(BusinessIdeaResult.class, "business_idea_result"),
                Map.entry(BusinessIdeaOption.class, "business_idea_option"),
                Map.entry(SimulationResult.class, "simulation_result"),
                Map.entry(SimulationDetail.class, "simulation_detail"),
                Map.entry(SupportProgramMatch.class, "support_program_match"),
                Map.entry(SupportProgramRecommendation.class, "support_program_recommendation"),
                Map.entry(BusinessPlan.class, "business_plan"),
                Map.entry(BusinessPlanSection.class, "business_plan_section"),
                Map.entry(OperationFeedback.class, "operation_feedback"),
                Map.entry(OperationMetric.class, "operation_metric"),
                Map.entry(SnsContent.class, "sns_content"),
                Map.entry(SnsContentItem.class, "sns_content_item"),
                Map.entry(SavedResult.class, "saved_result"));

        tables.forEach((entityClass, tableName) -> {
            assertThat(entityClass.isAnnotationPresent(Entity.class)).isTrue();
            assertThat(entityClass.getAnnotation(Table.class).name()).isEqualTo(tableName);
        });
    }

    @Test
    void allEntitiesExposePrimaryKeyField() {
        Class<?>[] entityClasses = {
                User.class,
                StartupProfile.class,
                Workspace.class,
                Agent.class,
                ChatRoom.class,
                ChatMessage.class,
                ChatAgentParticipant.class,
                BusinessIdeaResult.class,
                BusinessIdeaOption.class,
                SimulationResult.class,
                SimulationDetail.class,
                SupportProgramMatch.class,
                SupportProgramRecommendation.class,
                BusinessPlan.class,
                BusinessPlanSection.class,
                OperationFeedback.class,
                OperationMetric.class,
                SnsContent.class,
                SnsContentItem.class,
                SavedResult.class
        };

        for (Class<?> entityClass : entityClasses) {
            Field idField = Arrays.stream(entityClass.getDeclaredFields())
                    .filter(field -> field.getName().equals("id"))
                    .findFirst()
                    .orElseThrow();

            assertThat(idField.isAnnotationPresent(Id.class)).isTrue();
            assertThat(idField.getType()).isEqualTo(Long.class);
        }
    }
}
