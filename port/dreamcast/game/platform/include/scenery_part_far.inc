// Per-part rejection policy, shared by selection and ordinary drawing.
// The including scope provides d, foliage_near, meta, index, trans_pass and near
// where the corresponding build options enable them.
#if defined(RE4DC_FOLIAGE_TRIM)
            if(foliage_near){
                d.cull_far=foliage::kNear; // the placement's inside test was against the pass far: test its clusters
#if RE4DC_PS2_WORLD_LEAN
                d.lean_inside=false;
#endif
            }
#endif
#if defined(RE4DC_TRANS_POLICY) && RE4DC_NATIVE_FOG
            {   // TRANS_POLICY FAR: clusters past the room fog's threshold depth for this part's class are not drawn
                const float tf=trans::far_of(meta,index,trans_pass);
                if(tf>near && tf<d.cull_far){
                    d.cull_far=tf;
#if RE4DC_PS2_WORLD_LEAN
                    d.lean_inside=false;
#endif
                }
            }
#endif
