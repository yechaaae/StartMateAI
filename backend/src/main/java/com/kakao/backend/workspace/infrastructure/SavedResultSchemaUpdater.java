package com.kakao.backend.workspace.infrastructure;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.Statement;
import javax.sql.DataSource;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class SavedResultSchemaUpdater implements ApplicationRunner {

    private final DataSource dataSource;

    public SavedResultSchemaUpdater(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void run(org.springframework.boot.ApplicationArguments args) throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            String productName = connection.getMetaData().getDatabaseProductName();
            if (productName == null || !productName.toLowerCase().contains("mysql")) {
                return;
            }

            if (isReferenceIdNullable(connection)) {
                return;
            }

            try (Statement statement = connection.createStatement()) {
                statement.executeUpdate("ALTER TABLE saved_result MODIFY COLUMN reference_id BIGINT NULL");
            }
        }
    }

    private boolean isReferenceIdNullable(Connection connection) throws Exception {
        DatabaseMetaData metaData = connection.getMetaData();

        try (ResultSet resultSet = metaData.getColumns(connection.getCatalog(), null, "saved_result", "reference_id")) {
            if (!resultSet.next()) {
                return true;
            }

            int nullable = resultSet.getInt("NULLABLE");
            return nullable == DatabaseMetaData.columnNullable;
        }
    }
}
