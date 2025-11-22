# Maintainers

This document outlines the maintainer structure, responsibilities, and processes for the Bindu project.

## Current Maintainers

### Lead Maintainer

- **Raahul Dutta** ([@raahul](https://github.com/raahul)) - `raahul@getbindu.com`
  - Project founder and lead architect
  - Final decision authority on project direction
  - Release management and versioning


## Maintainer Responsibilities

Maintainers are trusted contributors who have demonstrated:

1. **Technical Excellence**
   - Deep understanding of the Bindu architecture and A2A/AP2/X402 protocols
   - Consistent high-quality code contributions
   - Strong testing and documentation practices

2. **Community Leadership**
   - Active participation in discussions and code reviews
   - Helping other contributors and users
   - Promoting best practices and project standards

3. **Project Stewardship**
   - Triaging and managing issues
   - Reviewing and merging pull requests
   - Maintaining project documentation
   - Ensuring test coverage stays above 70%

## Maintainer Privileges

Maintainers have:

- Write access to the main repository
- Authority to merge pull requests
- Ability to create releases (with lead maintainer approval)
- Access to project infrastructure (CI/CD, Discord moderation, etc.)
- Voting rights on major technical decisions

## Becoming a Maintainer

We welcome new maintainers who share our vision for the Internet of Agents. Here's the path:

### Requirements

1. **Sustained Contributions** (3+ months)
   - Multiple merged PRs demonstrating technical competence
   - Contributions across different areas (code, docs, tests, examples)
   - Active participation in issue discussions and code reviews

2. **Technical Expertise**
   - Understanding of agent frameworks (Agno, CrewAI, LangChain, etc.)
   - Knowledge of A2A protocol and DID-based identity systems
   - Familiarity with Python async patterns and FastAPI

3. **Community Engagement**
   - Helpful and respectful communication
   - Active on Discord or GitHub discussions
   - Mentoring other contributors

### Process

1. **Nomination**
   - Current maintainers can nominate contributors
   - Self-nomination is also welcome via email to `raahul@getbindu.com`

2. **Review**
   - Lead maintainer reviews contribution history
   - Discussion with existing maintainers
   - Consideration of technical skills and community fit

3. **Onboarding**
   - Repository access granted
   - Introduction to maintainer workflows
   - Pairing with existing maintainer for first few reviews

## Maintainer Workflow

### Code Review Guidelines

- **Response Time**: Aim to review PRs within 48 hours
- **Quality Standards**: Ensure code follows DRY principles, is type-safe, and includes tests
- **Documentation**: Verify that changes are documented
- **Breaking Changes**: Flag any breaking changes for lead maintainer review

### Release Process

1. **Version Bumping** (following semantic versioning)
   - Patch: Bug fixes, minor improvements
   - Minor: New features, backward-compatible changes
   - Major: Breaking changes

2. **Release Checklist**
   - [ ] All tests passing (coverage ≥70%)
   - [ ] CHANGELOG.md updated
   - [ ] Version bumped in `pyproject.toml`
   - [ ] Documentation updated
   - [ ] Lead maintainer approval

3. **Publishing**
   ```bash
   # Build and publish to PyPI
   uv build
   twine upload dist/*
   ```

### Issue Triage

- **Labeling**: Apply appropriate labels (bug, enhancement, documentation, etc.)
- **Prioritization**: Mark critical issues and security vulnerabilities
- **Assignment**: Assign to appropriate maintainer or contributor
- **Closure**: Close stale issues after 30 days of inactivity (with warning)

## Decision Making

### Minor Decisions
- Code style, documentation improvements, bug fixes
- **Process**: Single maintainer approval

### Major Decisions
- Architecture changes, breaking API changes, new protocol support
- **Process**: Discussion among maintainers, lead maintainer has final say

### RFC Process (for significant changes)
1. Create an RFC document in `docs/rfcs/`
2. Open discussion period (minimum 1 week)
3. Address feedback and iterate
4. Lead maintainer approval required

## Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Discord**: Real-time chat, community support - [Join here](https://discord.gg/3w5zuYUuwt)
- **Email**: Private maintainer discussions - `raahul@getbindu.com`
- **Weekly Community Meetup**: Online meetup every week to discuss project updates, roadmap, and community questions
  - Schedule announced on Discord and GitHub Discussions
  - Open to all contributors and community members
  - Recordings shared for those who cannot attend live

## Code of Conduct

All maintainers must uphold our community standards:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project and community
- Acknowledge and credit contributions

Violations should be reported to `raahul@getbindu.com`.

## Stepping Down

Maintainers can step down at any time by:
1. Notifying the lead maintainer
2. Documenting any ongoing work
3. Transferring responsibilities

We're grateful for all contributions, regardless of duration.

---

## Questions?

If you're interested in becoming a maintainer or have questions about the process, reach out:

- **Discord**: [Join our community](https://discord.gg/3w5zuYUuwt)
- **Email**: raahul@getbindu.com
- **GitHub**: Open a discussion

We're excited to grow the Bindu maintainer team and build the Internet of Agents together! 🌻
