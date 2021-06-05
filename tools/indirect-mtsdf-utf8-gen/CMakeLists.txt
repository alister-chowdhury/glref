
add_executable(indirect-mtsdf-utf8-gen
    main.cpp
)

target_compile_features(indirect-mtsdf-utf8-gen PUBLIC cxx_std_17)
target_link_libraries(indirect-mtsdf-utf8-gen
    PRIVATE
        msdfgen::msdfgen
        msdfgen::msdfgen-ext
        docopt_s
        glref_threading_helper
)
