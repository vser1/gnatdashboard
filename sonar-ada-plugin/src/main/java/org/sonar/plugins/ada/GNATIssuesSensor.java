/*
 * Sonar Ada Plugin
 *  Copyright (C) 2012-2013, AdaCore
 */
package org.sonar.plugins.ada;

import org.apache.commons.configuration.Configuration;
import org.sonar.api.batch.Sensor;
import org.sonar.api.batch.SensorContext;
import org.sonar.api.resources.Project;
import org.sonar.api.rules.Rule;
import org.sonar.api.rules.RuleFinder;
import org.sonar.api.rules.RuleQuery;
import org.sonar.api.rules.Violation;
import org.sonar.plugins.ada.persistence.AdaDao;
import org.sonar.plugins.ada.resources.AdaFile;
import org.sonar.plugins.ada.utils.AdaUtils;

public class GNATIssuesSensor implements Sensor {

    private RuleFinder ruleFinder;
    private Configuration config = null;
    private AdaDao dao = new AdaDao();

    public GNATIssuesSensor(Configuration config) {
        this.config = config;
    }

    public GNATIssuesSensor(RuleFinder ruleFinder, Configuration config) {
        this.ruleFinder = ruleFinder;
        this.config = config;
    }

    @Override
    public boolean shouldExecuteOnProject(Project project) {
        return Ada.KEY.equals(project.getLanguageKey());
    }

    @Override
    public void analyse(Project project, SensorContext context) {
        AdaUtils.LOG.info("----------  Issues Sensor");
        // Fetch all violation from the DB
        for (Violation v : dao.selectAllViolations()) {
            AdaUtils.LOG.info("*** Issue: {} -- for resource: {}", v.getMessage(), v.getResource().getName());
            // Try to find rule for the given rule repository
            RuleQuery ruleQuery = RuleQuery.create().withRepositoryKey(v.getRule().getRepositoryKey()).withKey(v.getRule().getKey());
            Rule rule = ruleFinder.find(ruleQuery);
            AdaUtils.LOG.info("Rule: {}", rule.getName());

            if (rule != null) {

                AdaFile res = (AdaFile) context.getResource(v.getResource());

                if (res != null) {
                    v.setRule(rule);
                    v.setResource(res);
                    context.saveViolation(v);
                } else {
                    AdaUtils.LOG.info("Cannot find the file '{}', skipping issue'{}'", v.getResource().getLongName(), v.getMessage());
                }
            } else {
                AdaUtils.LOG.warn("Cannot find the rule {}, skipping issue", v.getRule().getKey());
            }
        }
    }
}