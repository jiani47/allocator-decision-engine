import type { Claim } from "@/context/WizardContext"

export interface MatchedClaim {
  index: number // 1-based citation number
  claim: Claim
}

/**
 * Inject citation markers into memo text by finding verbatim source_text matches.
 * Returns the annotated text and the list of matched claims (for numbering).
 */
export function injectCitationMarkers(
  memoText: string,
  claims: Claim[],
): { annotatedText: string; matchedClaims: MatchedClaim[] } {
  const matchedClaims: MatchedClaim[] = []
  let annotated = memoText

  for (const claim of claims) {
    if (!claim.source_text) continue

    const idx = annotated.indexOf(claim.source_text)
    if (idx === -1) continue

    const citationNumber = matchedClaims.length + 1
    matchedClaims.push({ index: citationNumber, claim })

    // Insert marker right after the matched source_text
    const insertPos = idx + claim.source_text.length
    annotated =
      annotated.slice(0, insertPos) +
      ` {{CITE:${citationNumber}}}` +
      annotated.slice(insertPos)
  }

  return { annotatedText: annotated, matchedClaims }
}
