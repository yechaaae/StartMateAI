package com.kakao.backend.domain;

import static org.assertj.core.api.Assertions.assertThat;

import com.kakao.backend.agent.domain.Agent;
import com.kakao.backend.commercialarea.domain.CommercialAreaMetric;
import com.kakao.backend.commercialarea.domain.Store;
import com.kakao.backend.chat.domain.ChatAgentParticipant;
import com.kakao.backend.chat.domain.ChatMessage;
import com.kakao.backend.chat.domain.ChatRequestStatus;
import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.idea.domain.BusinessIdeaResult;
import com.kakao.backend.marketing.domain.SnsContent;
import com.kakao.backend.marketing.domain.SnsContentItem;
import com.kakao.backend.operation.domain.OperationFeedback;
import com.kakao.backend.operation.domain.OperationMetric;
import com.kakao.backend.plan.domain.BusinessPlan;
import com.kakao.backend.plan.domain.BusinessPlanSection;
import com.kakao.backend.policy.domain.SupportProgram;
import com.kakao.backend.policy.domain.SupportProgramMatch;
import com.kakao.backend.policy.domain.SupportProgramRecommendation;
import com.kakao.backend.policy.domain.SupportProgramRule;
import com.kakao.backend.seed.domain.SeedKnowledgeItem;
import com.kakao.backend.simulation.domain.SimulationDetail;
import com.kakao.backend.simulation.domain.SimulationResult;
import com.kakao.backend.user.model.User;
import com.kakao.backend.startupProfile.model.StartupProfile;
import com.kakao.backend.workspace.domain.SavedResult;
import com.kakao.backend.workspace.domain.Workspace;
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
                Map.entry(ChatRequestStatus.class, "chat_request_status"),
                Map.entry(ChatAgentParticipant.class, "chat_agent_participant"),
                Map.entry(BusinessIdeaResult.class, "business_idea_result"),
                Map.entry(BusinessIdeaOption.class, "business_idea_option"),
                Map.entry(SimulationResult.class, "simulation_result"),
                Map.entry(SimulationDetail.class, "simulation_detail"),
                Map.entry(SupportProgramMatch.class, "support_program_match"),
                Map.entry(SupportProgramRecommendation.class, "support_program_recommendation"),
                Map.entry(SupportProgram.class, "support_programs"),
                Map.entry(SupportProgramRule.class, "support_program_rules"),
                Map.entry(BusinessPlan.class, "business_plan"),
                Map.entry(BusinessPlanSection.class, "business_plan_section"),
                Map.entry(OperationFeedback.class, "operation_feedback"),
                Map.entry(OperationMetric.class, "operation_metric"),
                Map.entry(SnsContent.class, "sns_content"),
                Map.entry(SnsContentItem.class, "sns_content_item"),
                Map.entry(SavedResult.class, "saved_result"),
                Map.entry(Store.class, "stores"),
                Map.entry(CommercialAreaMetric.class, "commercial_area_metrics"),
                Map.entry(SeedKnowledgeItem.class, "seed_knowledge_items"));

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
                ChatRequestStatus.class,
                ChatAgentParticipant.class,
                BusinessIdeaResult.class,
                BusinessIdeaOption.class,
                SimulationResult.class,
                SimulationDetail.class,
                SupportProgramMatch.class,
                SupportProgramRecommendation.class,
                SupportProgram.class,
                SupportProgramRule.class,
                BusinessPlan.class,
                BusinessPlanSection.class,
                OperationFeedback.class,
                OperationMetric.class,
                SnsContent.class,
                SnsContentItem.class,
                SavedResult.class,
                Store.class,
                CommercialAreaMetric.class,
                SeedKnowledgeItem.class
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
