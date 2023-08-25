#version 460 core

layout(location=0) in uint type;
layout(location=0) out uint outType;


void main()
{
    outType = type;
}
