REFLEXION_PROMPT = """
You previously answered:

{answer}

Evaluation feedback:
- BLEU score was low
- The response missed key factual alignment

Improve the answer by:
1. Being more factual
2. Grounding explicitly in retrieved data
3. Avoiding vague language
"""

def reflexion_rerun(query, bad_answer, run_chain_fn):
    corrective_prompt = REFLEXION_PROMPT.format(answer=bad_answer)

    improved_answer = run_chain_fn(
        query,
        system_override=corrective_prompt
    )
    return improved_answer
