# MrPackMaker 1.9.0 architecture

1.8.x remains the generation/export path. 1.9.0 adds an approval-gated change
layer around it:

`prompt -> intent -> discovery -> plan -> approval -> apply -> dependency repair -> compatibility -> export`

New services are pure orchestration/domain modules. They call existing resolver,
scoring, dependency graph, compatibility and MRPack writer boundaries instead of
copying them. Database changes are additive: history, AI requests, imports and
repair reports. A plan is never applied by the AI request endpoint; the client
must explicitly approve its plan id.
