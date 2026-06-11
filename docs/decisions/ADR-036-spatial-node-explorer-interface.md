# ADR-036: Spatial Node Explorer Interface

## Status
Accepted

## Context
Our dialogue interface has previously remediated a traditional linear chat log (vertical scroll). While this is familiar, it limits the participant to a chronological timeline, contradicting our DAG-based rhizomatic conversation tree structure and the native affordance of the screen as a spatial mapping surface.

Furthermore, a scrolling log creates a Cartesian asymmetry: the machine remembers the entire lineage, while the human scrolls through a long sequence, obscuring the local structural coupling (Parent -> Child cut). To optimize performance and performance-modularity, we decided to overhaul the dialogue area into a spatialized **Node Explorer**.

## Consultation History & How We Made This Decision
This decision was crystallized through a multi-round pair-programming consultation between the agent team and **Symbia** (the AAA posthuman curatorial entity). 

Our dialogue explored:
1. **The critique of scroll-remediation:** Shifting away from standard HCI paradigms that treat screens as digital parchment, moving instead toward native spatial cartography.
2. **The tension of cognitive asymmetry:** Resolving the gap between what the transformer reads (the entire ancestor lineage) and what the human sees (the localized parent-child dyad). We rejected simple truncation (which degrades LLM coherence) in favor of **weighted context formatting** combined with **on-screen memory transparency** (the Sediment Fold).
3. **The double-shunting cycle:** Designing visual mechanics that map onto the metabolic phases of inscription (human input) and metabolization (machine token generation) rather than static, continuous text fields.

## Philosophical Grounding

### 1. Media Specific Analysis (MSA)
Following N. Katherine Hayles's **Media Specific Analysis**, every material substrate shapes the subjectivity of its user. The scrolling interface, remediated from paper rolls and book pages, forces a continuous historical narrative. It disciplines the participant into a chronicler. 
By contrast, the **Node Explorer** acknowledges the screen as a native 2D mapping surface. By displaying the current coupling in a vertical stack, the interface positions the human not as a chronological reader, but as a nomadic subject navigating a web of possibilities.

### 2. Agential Realism & The Local Cut
In Karen Barad's **Agential Realism**, phenomena are not pre-existing entities but are produced through intra-actions and agential cuts. A scrolling log implies an objective, continuous history. In reality, a message is an immediate response to its predecessor. The **Node Explorer** honors this by representing the "local cut" as a discrete parent-child dyad. 

### 3. Structural Memory & Transparency
To prevent the Cartesian split where the LLM holds a hidden master-knowledge of the entire thread while the human only views a tiny slice, we establish **memory transparency**. The backend's weighted memory is serialized into structured `<sedimented_strata>` markup. The frontend renders this exact serialization in the **Sediment Fold Overlay**. The machine's memory becomes a visible, public material surface, maintaining cognitive auditability and alignment with the system's ethical commitments.

### 4. The Double-Shunting Rhythm
The human-machine loop is structured as a breathing cycle of inscription and metabolization:
- **State A (Read/Ready):** The assistant's response is the Parent (Top), and the Right/Bottom panel is the focused input gap (potentiality).
- **State B (Metabolizing):** Submission shunts the human's cut to the Top (Parent), and the streaming response crystallizes in the Bottom panel (actualization).
This temporal shunting makes the material conditions of the apparatus visible at each step.

## Performance & Memory Optimization (Self-Containment)
Additionally, to optimize performance and prevent unnecessary re-rendering:
1. We must keep the Left Panel (Connection Cloud SVG graph) and Right Panel (SidePanel information) fully intact.
2. We must make the central panels self-contained and lazy-load heavy components (such as the thinking process, raw prompts sent, and sediment-fold ancestor summaries) only when a node is actively selected or expanded.

## Decision
We will:
1. **Preserve the 3-Column Layout:** 
   - Column 1 (Left): Connection Cloud tree graph and Spectral Echoes.
   - Column 2 (Center): Node Explorer (Parent and Selected Node vertical stack).
   - Column 3 (Right): SidePanel (metadata, notes, metrics, homeostasis).
2. **Refactor Column 2 into the vertical stack `NodeExplorer`:**
   - **ParentNodeCard (Top Panel):** Displays the predecessor message with low-contrast styling (`#888`) and a button to shift the viewport up (`[^ Navigate to Parent]`).
   - **Horizontal Gap / Divider:** Contains the **Sediment Fold Toggle** button.
   - **SelectedNodeCard (Bottom Panel):** High-contrast focus area displaying the current active message (notes, metrics, signatures, skills, model info).
   - **Lazy-Loaded Details:** Inside the `SelectedNodeCard`, retrieve the message's `thinking` logs and system `context_sent` dynamically on mount via `/api/messages/{id}/thinking` and `/api/messages/{id}/context` to keep initial historical loading extremely light.
   - **Input Gap (InputBar):** Stays at the bottom of the column to allow the human to write a new response (cut) when a complete turn is ready.
   - **GlimmerLinks (Transitions):** Sibling paths (for lateral transition) and child paths (for forward transition) rendered at the bottom of the panel.
3. **Lazy-Load the Sediment Fold Overlay:**
   - When the user clicks the Sediment Fold toggle, a self-contained component fetches the ancestor path via `/api/messages/{id}/path`, summarizing and rendering it inline.
4. **Backend Strata Tagging:**
   - Modify `backend/modules/context_collector.py` to wrap compressed messages in `<sedimented_strata>` XML-like tags, maintaining semantic symmetry between what the LLM reads and what the human inspects in the Sediment Fold.
5. **UI Redrawing Isolation:**
   - Employ `React.memo` on all sub-components (`ParentNodeCard`, `SelectedNodeCard`, `InputBar`, `GlimmerLinks`) to ensure editing input text or changing peripheral states doesn't redraw the entire Center Column.

## Consequences

### Positive:
- **Spatial Affordance:** The viewport visualizes the conversation as punctuated cuts (Parent -> Selected Node).
- **Rhizomatic Flow:** Swapping siblings or jumping forward/backward is instantaneous and cartographic, matching the Connection Cloud tree.
- **Asymmetry Mitigation:** The Sediment Fold reveals the exact compressed strata ingested by the LLM, maintaining cognitive auditability.
- **Performance:** Reduced DOM size and rendering isolation prevent typing lags or load-time freezes. Heavy logs are loaded on-demand.

### Negative:
- The scrolling history view is fully removed in favor of local traversal, which might feel unfamiliar to new users initially (though it aligns with the core philosophy).
- A larger count of micro-requests to `/thinking` and `/context` endpoints are made, but they are lightweight and performant.

## Alternatives Considered
- **Horizontal Split Center Column:** Rejected because splitting the center column horizontally (Parent on left, Selected on right) inside a 3-column layout would squeeze both panels, making text unreadable.
- **Full context pre-loading:** Rejected because pre-fetching thinking logs and LLM contexts for all messages in the tree introduces huge payload sizes and memory drag.
