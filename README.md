![](https://socialify.git.ci/yv1ing/MollyAudit/image?language=1&owner=1&name=1&stargazers=1&theme=Light)

# What's this?

This is an automatic code auditing tool based on LangChain and driven by LLMs.

**Basic idea:**

I designed two agents, one called Code Audit Engineer (CAE) and another called Code Software Architect (CSA). CSA is responsible for functionally dividing the project structure to be audited and then passing it to CAE as a reference.

After CAE collects the project structure, it independently determines the actions of the audit code and outputs the action instructions in a specific format. The local program parses the instructions and sends the relevant results, thus forming an automatic workflow.

At present, this tool is still in an immature stage and there are still many problems. If you have better suggestions, please contact me!


# Tool interface

![](assets/img-01.png)