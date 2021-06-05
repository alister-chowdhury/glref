#pragma once

#include <utility>

#ifdef GLREF_TBB_SUPPORT
    #include <tbb/parallel_for.h>
    #include <tbb/parallel_for_each.h>
    #include <tbb/parallel_invoke.h>
#endif


template<typename IterT, typename F>
void glrefParallelFor(
    #ifdef GLREF_TBB_SUPPORT
    IterT&& begin,
    IterT&& end,
    #else
    const IterT begin,
    const IterT end,
    #endif
    F&& func
) {
    #ifdef GLREF_TBB_SUPPORT
        tbb::parallel_for(
            std::forward<IterT>(begin),
            std::forward<IterT>(end),
            std::forward<F>(func)
        );
    #else
        for(IterT iter=begin; iter<end; ++iter)
        {
            func(iter);
        }
    #endif
}


template<typename IterT, typename F>
void glrefParallelForEach(
    #ifdef GLREF_TBB_SUPPORT
    IterT&& begin,
    IterT&& end,
    #else
    const IterT begin,
    const IterT end,
    #endif
    F&& func
)
{
    #ifdef GLREF_TBB_SUPPORT
        tbb::parallel_for_each(
            std::forward<IterT>(begin),
            std::forward<IterT>(end),
            std::forward<F>(func)
        );
    #else
        for(IterT iter=begin; iter<end; ++iter)
        {
            func(*iter);
        }
    #endif
}

template<typename... F>
void glrefParallelInvoke(F&&... fs)
{
    #ifdef GLREF_TBB_SUPPORT
        tbb::parallel_invoke(std::forward<F>(fs)...);
    #else
        (fs(), ...);
    #endif
}
