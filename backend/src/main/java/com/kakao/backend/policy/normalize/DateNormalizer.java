package com.kakao.backend.policy.normalize;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class DateNormalizer {

    private static final Pattern DATE_PATTERN = Pattern.compile("(20\\d{2})[.\\-/년\\s]*(\\d{1,2})[.\\-/월\\s]*(\\d{1,2})");

    public LocalDate firstDate(String raw) {
        List<LocalDate> dates = dates(raw);
        return dates.isEmpty() ? null : dates.get(0);
    }

    public LocalDate lastDate(String raw) {
        List<LocalDate> dates = dates(raw);
        return dates.isEmpty() ? null : dates.get(dates.size() - 1);
    }

    public List<LocalDate> dates(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        List<LocalDate> dates = new ArrayList<>();
        Matcher matcher = DATE_PATTERN.matcher(raw);
        while (matcher.find()) {
            int year = Integer.parseInt(matcher.group(1));
            int month = Integer.parseInt(matcher.group(2));
            int day = Integer.parseInt(matcher.group(3));
            dates.add(LocalDate.of(year, month, day));
        }
        if (!dates.isEmpty()) {
            return dates;
        }
        for (DateTimeFormatter formatter : List.of(DateTimeFormatter.BASIC_ISO_DATE, DateTimeFormatter.ISO_LOCAL_DATE)) {
            try {
                return List.of(LocalDate.parse(raw.trim(), formatter));
            } catch (DateTimeParseException ignored) {
                // Try the next common public-data date format.
            }
        }
        return List.of();
    }
}
