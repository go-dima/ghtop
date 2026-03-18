#### ghtop

The purpose: View running GH actions for repos, prs.
The beahavior should be like k9s/htop - browse using arrows, enter/back to navigate, q to exit

###### Hierarchy
    - orgs/repos he can chhose from
    - repos in the org - organized by recency (github dffault)
    - pull requests by recency with metadata
    - actions of pull request - name, progress, status

###### Capabilities
    - User can see his PRs only (a view)
    - User can search for prs by name toi filter (fuzzy search)
    - User can open a pr in web view
    - User can view pr details and actions status (like `gh run view`)
    - User can trigger a run
    - Arrow naviagtion

###### Tech Requirements
    - python or golang implementation
    - base on `gh` tool
    - authentication is done extenrnally - app assumes auth is solved

###### Reference:
    - https://github.com/htop-dev/htop - original repo
    - [https://github.com/DeanLa/cctop](https://github.com/DeanLa/cctop/tree/worktree-refactor/async-workers) - a simple clone that allows watching claude processes
    - https://github.com/derailed/k9s - a tool to monitor k8s pods


---
Your task is to help me plan a tool like this. Look for references, ask questions and we want to create a full spec.
Consider quick python-based implementation and elaborate golan based tool
**The expected output is a plan that can be read and refined more. No code needed.**