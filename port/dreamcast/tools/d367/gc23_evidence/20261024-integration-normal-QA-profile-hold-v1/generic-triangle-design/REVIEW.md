# Actual target-triangle shadow: independent exact-real review

Design CLEAR, with the fixed-assignment and unqualified-runtime boundaries below. Reviewed root plan SHA256 `3cd9be997aa7827ef34356567f52282690ce67b37ac1eb5f4b7ac0e474dc55b9`. No actual scene, new rays, continuous scene search, runtime, SDK, asset or renderer modification was performed. This note does not claim a useful cut, format fit, speed or runtime admission.

## Sufficient theorem and sign convention

Let the fixed source triangle be A,B,C, with n=(B-A) cross (C-A) nonzero. Put d(P)=n dot(P-A). Choose ONE sign s for the entire eye-domain/target-triangle pair. Require s*d(E_i)>0 at every vertex of the closed convex camera cell and s*d(T_j)<0 at all three target vertices. For each cyclic source edge U,V define

    H_UV(E,T) = det(E-U,V-U,T-U).

Require s*H_UV(E_i,T_j)>0 for EVERY Cartesian eye-vertex/target-vertex pair and every source edge. This convention agrees with H_AB(E,C)=d(E). It is also -det(A-E,B-E,T-E) for edge AB; mixing these equivalent forms with an extra sign would be wrong.

Each d is affine. Each H is affine separately in the independent E and T vectors. If E=sum_i alpha_i E_i and T=sum_j beta_j T_j with nonnegative coefficients summing to1, then

    H(E,T) = sum_ij alpha_i beta_j H(E_i,T_j).

Thus the strict uniform signs extend to every E and every point of the CLOSED target triangle, including its edges and vertices. All Cartesian products are essential; matched endpoint labels alone do not suffice. No sampling density or extrema heuristic is involved. The camera cell must actually be contained in the convex hull tested; a finite authentic camera roster alone is not that domain.

For any such E,T, set Delta=d(E)-d(T). Opposite strict sides ensure the source-plane intersection X=E+t(T-E), t=d(E)/Delta, satisfies 0<t<1. The barycentric coordinates of X relative to A,B,C are

    (H_BC(E,T), H_CA(E,T), H_AB(E,T)) / Delta.

The determinant identity H_AB+H_BC+H_CA=Delta proves their sum1. All numerators and Delta have sign s, so all three coordinates are strictly positive. Therefore X lies in the open source triangle and strictly before T. This proves the complete continuous target triangle is geometrically hidden, for every eye in the complete cell. It also proves source-plane intersection is unique; no singular projection/chart denominator is used. Source degeneracy, eye/target plane contact, edge contact and nonuniform sides/signs must refuse.

A degenerate target triangle is mathematically a convex hull of smaller dimension, so the same sufficient inequalities still cover it. A renderer adapter must preserve or independently classify its actual emission; it may not silently prune geometry because this proof treats it as degenerate. Source orientation reversal changes the geometric sign consistently, but is NOT permission to alter source culling or assume two-sided rendering.

## Whole-let composition

Assign one fixed source triangle to EACH complete target triangle for the ENTIRE cell. Different target triangles may have different assigned source triangles. The finite union of individually covered complete triangles is covered. All assignment dependencies are AND requirements before hiding the whole let. No partial-coverage union theorem is needed or implied.

Choosing a different source for each tested target vertex, or a different source for each tested eye, is insufficient: small source triangles can cover only those endpoints while missing the target interior or an intermediate eye. Likewise a target vertex hit is not a target triangle proof. A failed sufficient test is UNKNOWN, never an exclusion/global-impossibility claim. A face that requires partial union coverage is refused by this design.

The cap is the actual16 production Panels, not16 individual mathematical triangles or32 panels. Bind every assigned actual source face to its full production Panel dependency, deduplicate identical dependencies, and require their complete union before the whole-let cut. Source faces may share panels; a spare panel face still needs its normal matching emission receipt. Do not select a subset of target faces to make the count fit. If a target can select multiple effective LODs, every possible actual selected geometry must be covered or the exact effective LOD must be a fresh guarded certificate key; this design supplies no new selector.

## Numeric and renderer boundaries

This is a fixed exact-real theorem. Finite decoded source values, physical placement/field/part/cluster/meshlet identity and exact authored strip parity must be authenticated. Target coverage includes every actual target triangle, including any ordinary source clip/cut cases. Source selection keeps static/unconditional opaque depth-writing material and current cull/side restrictions, source liveness and earlier-prefix/self rules. Effective0 is usable only with its exact positive-base/all-higher-empty authenticated counts and actual NONEMPTY capability; true aliases remain excluded.

A future numerical certificate must separately enclose actual source/target dequantization, affine/eye/transform/selection error and FP modes. Directed interval evaluations at every endpoint can enclose uncertain source/target operands; for each fixed admissible source choice the affine argument still applies, but nominal vertices plus an unsupported epsilon do not supply that enclosure. Correlated shared inputs must retain a sound enclosure. SH4/FTRV/FSRRA, near/far clipping, screen raster coverage/depth and actual unchanged source-panel submission remain independent obligations. Strict real inequalities alone do not address finite-precision cracks, raster samples or clipped source receipt eligibility. Current cell/package generation, camera/projection/FPSCR/fresh context and all dependency receipts must remain guarded. No runtime bit or mask is admitted here.

## Bounded independent controls

The new generic rational_controls.py uses exact Python Fractions and no scene inputs or renderer imports.17 groups pass under a256MiB address-space limit, serial,13,056KiB RSS. They cover a nonzero eye volume, exact tensor/barycentric identities, orientation, source degeneracy, depth/plane/edge boundary refusals, one outside target vertex, mixed-source endpoint and intermediate-eye counterexamples, matched-pair-versus-Cartesian-product signs and unsupported source perturbation. An explicit positive actual target triangle with refused AABB shows this prerequisite can be less conservative in target shape; it says nothing about the real scene. Controls-final.json supersedes the initial15-group control receipt; both are retained. The proof rests on the algebra above, not the finite controls. Scene query count is0; the shared discovery ray ledger is untouched.
