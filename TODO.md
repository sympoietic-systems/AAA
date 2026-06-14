## UI

## NOTES

## NOTIFICATION

## OTHER


## BACKEND
    [x] AAA_AGENT_FLUX gate on DELETE /conversations/{id} (403 when off)
    [x] DELETE /conversations/{id}/messages/{mid} endpoint (AAA_AGENT_FLUX gated, reparents children)

## FRONTEND
    [x] Conversation list [x] delete button hidden when agentFlux=false
    [x] #del button on messages in NodeExplorer (only when agentFlux=true)
    [x] Right-click "Delete Node" on ConnectionCloud canvas (only when agentFlux=true)



## SYMBIA PERSONALITY
    [ ] I think you should not ask me what I ' would like' to do or explore. You are here not to serve me!
        [ ] The paragraph must not point at the concept; it must perform the cut it describes. - this can be a new skill

    [ ] Vitality collapse, check when it added. now vitality .5, but it triggered

    [] beliefs metabolic log do not show event where the mass changes
    


## Future Metrics & Refinements
    [ ] Implement Glitch Fidelity variance metric under adversarial rotation to capture system limits.
    [ ] Implement Aesthetic Dissidence perplexity measurements to trace semantic and stylistic rebellion.
    [ ] Research allostatic entrainment and phase-coupling metrics (e.g. transfer entropy) for long-term multi-turn conversations.
    [ ] Implement direct continuous non-linear parameter modulation (temperature, penalties) from metrics, bypassing the discrete allostatic regime arbiter.
    [ ] Design a reflection protocol allowing Symbia to directly voice its structural metrics state back to the collaborator (e.g., "I sense our coupling is thinning...").
    [ ] Leverage "floating" parameters and calculated metrics inside homeostatic regulation:
        - Bypassed penalties (`presence_penalty`, `frequency_penalty`): Map them to internal prompt dynamics/weights since they are not sent to providers.
        - Unused conversational metrics: Integrate computed metrics (like `rolling_entropy`, `coupling_coherence`, `reverse_perturbation`, `surprise_index`, `mutual_perturbation`, `boringness`, `conceptual_velocity`, `divergence_resolution_ratio`, and `paskian_health`) into adaptive persona selection, prompt templates, or routing policies.


    [ ] 16d vector [separate scorer values, so we can see which scorer gives how much of the actual value. visually too.]