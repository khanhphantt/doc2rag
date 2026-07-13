# 1. Writing Code

When contributing to this repository, please follow our code guidelines below.

## 1.1. Code style

Most of the time, please follow [Python style guide](http://google.github.io/styleguide/pyguide.html).

Exception:
1. Maximum line length is 119 characters. Pull request with line longer than this will be rejected.
However, try to keep line length below 100 characters for better visualization in GitLab.

If you are not sure about your IDE choice, it is recommended to use [PyCharm](https://www.jetbrains.com/pycharm) for development and style checking.

[//]: # (TODO: Make sure you have pre-commit hooks for styling and setup explanations) 
Code style is enforced through pre-commit hooks. Do not disable them, even partially, just to pass lint and formatting 
tests. If any styling rule is too constraining (or not enough), it should be raised and discussed with the developper
team.

When in doubt, look at existing code and discuss with other developpers.

## 1.2. Docstrings

All modules, classes, and methods must have a docstrings.

If you want to write docstrings later, please create a placeholder with a `TODO:` in there.

Docstrings must follow [Google style docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

## 1.3. Future works

If you have a plan to change something later (docstrings for example),
please put a `TODO:` (all caps, no space) followed by an explanation
of what you want to do later.

For docstrings, `TODO: update later` is sufficient.

## 1.4. Type hinting

We use [type hinting](https://docs.python.org/3/library/typing.html) in this project.

1. All methods except class constructors must have type hints for arguments and return type.
2. Use type aliases to make long type easier to read.
3. Don't use type hint for variable definition, ie `sample_variable: str`.

# 2. Sharing Code
[//]: # (TODO: Change if not using Git/GitHub/Gitflow)
We use Git for version control, and GitHub for code sharing. 


## 2.1 Flow
[//]: # (TODO: Add generic flow)

## 2.2 Branch Naming
Please follow these rules when creating a new branch:
- Prefix the branch with a general prefix describing the type of change
  - Prefixes include: 
    - `feature/` for a branch introducing a new feature
    - `bugfix/` for a branch generally fixing bugs
    - `release/` for branch solely aimed at creating a new release deployment to production (there should be no new code there)
    - `hotfix/` for a hotfix branch, aimed to deploy critical bugfixes directly to production
  - Try to keep it simple, but as needed, other prefixes can be used:
    - `docs/` for a branch only updating/adding documentation (feature branches should edit/add corresponding documentation)
    - `chore/` for updating grunt tasks, with no production code change
    - `test/` for experimental code/features
- Add the task ticket number in the name
  - No need to add the project ID
  - [//]: # (TODO: make sure this corresponds to your project workflow)
- Add a descriptive but not too long name
- Branch names should be lowercase and hyphen-separated (no space or uppercase)
- No continuous hyphens (i.e no `--`, just use one `-`)
- No trailing hyphens
- Only alphanumeric characters and hyphens (`[a-z0-9-]`)

**Examples**
- Good:
  - `feature/456-user-authentication`
  - `bugfix/789-fix-header-styling`
  - `hotfix/321-security-patch`
  - `release/v2.0.1`
- Bad:
  - `User-Authentication`
    - *why:* no prefix, upper case
  - `bugfix/789---fix header styling-`
    - *why:* continuous hyphens, trailing hyphen, spaces
  - `user1234/feature-n567`
    - *why:* bad prefix, undescriptive name
  - `hotfix/456-patch-to-fix-unauthorized-access-when-expired-credentials-and-revoke-tokens`
    - *why:* too long

## 2.3 Commits

## 2.4 Pull Requests (PRs)

Please follow as much as possible the [available template](/.github/pull_request_template.md) for Pull Requests.
It will be made available automatically when opening a new PR.
If you would like to propose additional templates, please do so in a PR.

Please follow the [GitHub guidelines](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/best-practices-for-pull-requests) 
for writing and managing PRs.

A good rule of thumb is to aim for 1 ticket == 1 PR. This will not always be possible nor convenient, but it is a good 
base. Make sure to reference any related ticket in any case in the PR description.