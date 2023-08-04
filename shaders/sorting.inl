#ifndef SORTING_TYPE
#define "You must define SORTING_TYPE, which should be the underlying type being sorted."
#endif

#ifndef SORTING_CONTEXT
#error "You must define SORTING_CONTEXT, which is a type to be passed to your custom functions."
#endif

#ifndef SORTING_COMP
#error "You must define SORTING_COMP, which is a function with the signature `bool f(SORTING_TYPE a, SORTING_TYPE b, inout SORTING_CONTEXT ctx)`"
#endif

#ifndef SORTING_LOAD
#error "You must define SORTING_LOAD, which is a function with the signature `SORTING_TYPE f(int a, inout SORTING_CONTEXT ctx)`"
#endif

#ifndef SORTING_SET
#error "You must define SORTING_LOAD, which is a function with the signature `void f(int a, SORTING_TYPE, inout SORTING_CONTEXT ctx)`"
#endif


#define SORTING_NAME_IMPL2_(x, y)   x ## y
#define SORTING_NAME_IMPL1_(x, y)   SORTING_NAME_IMPL2_(x, y)
#define SORTING_NAME_(y)            SORTING_NAME_IMPL1_(SORTING_NAME_PREFIX, y)


void SORTING_NAME_(iter_swap)(int a, int b, inout SORTING_CONTEXT ctx)
{
    SORTING_TYPE va = SORTING_LOAD(a, ctx);
    SORTING_TYPE vb = SORTING_LOAD(b, ctx);
    SORTING_SET(a, vb, ctx);
    SORTING_SET(b, va, ctx);
}


int SORTING_NAME_(med3)(int a, int b, int c, inout SORTING_CONTEXT ctx)
{
    SORTING_TYPE va = SORTING_LOAD(a, ctx);
    SORTING_TYPE vb = SORTING_LOAD(b, ctx);
    SORTING_TYPE vc = SORTING_LOAD(c, ctx);

    if(SORTING_COMP(va, vb, ctx))
    {
        return SORTING_COMP(vb, vc, ctx) ? b : ( SORTING_COMP(va, vc, ctx) ? c : a );
    }
    return SORTING_COMP(va, vc, ctx) ? a : ( SORTING_COMP(vb, vc, ctx) ? c : b );
}


void SORTING_NAME_(insertion_sort)(int start, int end, inout SORTING_CONTEXT ctx)
{
    int it = start; ++it;
    for(; it < end; ++it)
    {
        SORTING_TYPE value = SORTING_LOAD(it, ctx);
        int subit = it;
        int lastit = it; --lastit;

        for(; (lastit >= start) && SORTING_COMP(value, SORTING_LOAD(lastit, ctx), ctx); --subit, --lastit)
        {
            SORTING_SET(subit, SORTING_LOAD(lastit, ctx), ctx);
        }
        SORTING_SET(subit, value, ctx);
    }
}


void SORTING_NAME_(selection_sort)(int start, int end, inout SORTING_CONTEXT ctx)
{
    int last = end;
    --last;
    for(; start < last; ++start)
    {
        int s = start;
        int it = start; ++it;
        for(; it < end; ++it)
        {
            if(SORTING_COMP(SORTING_LOAD(it, ctx), SORTING_LOAD(s, ctx), ctx))
            {
                s = it;
            }
        }
        if(s != start)
        {
            SORTING_NAME_(iter_swap)(s, start, ctx);
        }
    }
}


void SORTING_NAME_(partial_selection_sort)(int start, int nth, int end, inout SORTING_CONTEXT ctx)
{
    for(; start <= nth; ++start)
    {
        int s = start;
        int it = start; ++it;
        for(; it < end; ++it)
        {
            if(SORTING_COMP(SORTING_LOAD(it, ctx), SORTING_LOAD(s, ctx), ctx))
            {
                s = it;
            }
        }
        if(s != start)
        {
            SORTING_NAME_(iter_swap)(s, start, ctx);
        }
    }
}


int SORTING_NAME_(partition_external)(int start, int end, SORTING_TYPE piv, inout SORTING_CONTEXT ctx)
{

    int last = end - 1;

    // Initial scan
    for(; (start <= last) && SORTING_COMP(SORTING_LOAD(start, ctx), piv, ctx); ++start);
    for(; (start < last) && (!SORTING_COMP(SORTING_LOAD(last, ctx), piv, ctx)); --last);

    // If the comparitor is unstable, e.g random, this is liable to access OOB memory
    while (start < last)
    {
        SORTING_NAME_(iter_swap)(start, last, ctx);
        while (SORTING_COMP(SORTING_LOAD(++start, ctx), piv, ctx));
        while (!SORTING_COMP(SORTING_LOAD(--last, ctx), piv, ctx));
    }

    return start;
}


int SORTING_NAME_(partition)(int start, int end, int piv, inout SORTING_CONTEXT ctx)
{
    int last = end - 1;

    if(piv != last)
    {
        SORTING_NAME_(iter_swap)(piv, last, ctx);
    }
    
    int result = SORTING_NAME_(partition_external)(start, last, SORTING_LOAD(last, ctx), ctx);
    
    if(result != last)
    {
        SORTING_NAME_(iter_swap)(result, last, ctx);
        
        // Handle the case where we have numerous duplicate values, rollback towards
        // the target pivot.
        if(result == start)
        {
            last = result;
            while((result != piv) && (!SORTING_COMP(SORTING_LOAD(result, ctx), SORTING_LOAD(++last, ctx), ctx)))
            {
                ++result;
            }
        }
    }

    return result;

}


void SORTING_NAME_(nth_element)(int start, int nth, int end, inout SORTING_CONTEXT ctx)
{
    int n = end - start;

    if(n > 1)
    {
        const int maxitersize = 50;
        int maxdepth = 32;

        while(true)
        {
            n = end - start;
            if(n <= 1)
            {
                break;
            }
            if(n <= maxitersize)
            {
                SORTING_NAME_(partial_selection_sort)(start, nth, end, ctx);
                break;
            }
            if(--maxdepth <= 0)
            {
                SORTING_NAME_(insertion_sort)(start, end, ctx);
                return;
            }

            int split = SORTING_NAME_(partition)(start, end, nth, ctx);

            while((split == start) && (split != nth))
            {
                ++start;
                n = end - start;
                split = SORTING_NAME_(partition)(start,
                                                 end,
                                                 start + n/2,
                                                 ctx);
            }

            if(split < nth)
            {
                ++split;
                start = split;
            }
            else if(split > nth)
            {
                end = split;
            }
            else
            {
                break;
            }
        }
    }
}



#undef SORTING_NAME_IMPL2_
#undef SORTING_NAME_IMPL1_
#undef SORTING_NAME_
