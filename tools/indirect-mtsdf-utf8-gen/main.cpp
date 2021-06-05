// Silence annoying warnings about using Micorsofts *_s safe versions of C functions.
#define _CRT_SECURE_NO_WARNINGS

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include <docopt.h>
#include <msdfgen.h>
#include <msdfgen-ext.h>

#include "../glref_thread_helper.h"


namespace
{

const static std::string g_pathSeperator =
#if defined(WIN32) || defined(_WIN32) || defined(__WIN32) && !defined(__CYGWIN__)
    "\\"
#else
    "/"
#endif
;


struct FontFileHeader
{
    uint16_t    width;
    uint16_t    height;
    uint8_t     layers;
    uint8_t     pixelRange;
};


struct FontData
{
    msdfgen::Projection                     projection;
    int                                     characterWidth;
    int                                     characterHeight;
    std::array<msdfgen::Shape, 0x10000>     shapes;
    double                                  pixelRange;
};


struct RenderedShapes
{
    std::array<msdfgen::Bitmap<float, 4>, 0x10000>     mtsdfRegions;
};


struct IndirectAndLayers
{
    msdfgen::Bitmap<uint16_t, 1>              indirect;
    std::vector<msdfgen::Bitmap<float, 4>>    layers;
};


struct HashBitmapHelper
{
    size_t operator()(const msdfgen::Bitmap<float, 4>& bmp) const
    {
        const float* data = (const float*)bmp;
        const std::string_view sv ((const char*)data, sizeof(float)*4*bmp.width()*bmp.height());
        return std::hash<std::string_view>{}(sv);
    }    
};


struct EqualBitmapHelper
{
    bool operator()(const msdfgen::Bitmap<float, 4>& a, const msdfgen::Bitmap<float, 4>& b) const
    {
        if(a.width() != b.width() || a.height() != b.height())
        {
            return false;
        }
        const float* aPtr = (const float*)a;
        const float* bPtr = (const float*)b;
        return std::memcmp(aPtr, bPtr, sizeof(float)*4*a.width()*a.height()) == 0;
    }
};


/**
 * @brief Pack indirect coordinates into a u16.
 * @details
 *     The layout returned should be:
 *         x:5;
 *         y:4;
 *         z:7;
 */
uint16_t packIndirectCoordinate(uint8_t x, uint8_t y, uint8_t z)
{
#if 0
    union
    {
        struct
        {
            uint16_t x:5;
            uint16_t y:4;
            uint16_t z:7;
        } field;
        uint16_t combined;
    } conversion;

    conversion.field.x = x;
    conversion.field.y = y;
    conversion.field.z = z;
    return conversion.combined;
#else
    // None bitfield-union version generates less instructions
    // (atleast on clang)
    const uint16_t z0 = uint16_t(z) << 9;
    const uint16_t y0 = uint16_t(y) << 5;
    const uint16_t result = x | y0 | z0;
    return result;
#endif
}


std::unique_ptr<FontData> loadFontData(const char* fontFilePath,
                                       const double scale=1.0,
                                       const int pixelRange_=1)
{
    msdfgen::FreetypeHandle* ftHandle = msdfgen::initializeFreetype();
    if(!ftHandle)
    {
        std::fprintf(stderr, "Unable to initialize freetype library!\n");
        std::abort();
    }

    msdfgen::FontHandle* fontHandle = msdfgen::loadFont(ftHandle, fontFilePath);
    if(!fontHandle)
    {
        std::fprintf(stderr, "Unable to load font file '%s'!\n", fontFilePath);
        std::abort();        
    }

    msdfgen::FontMetrics fontMetrics;
    if(!msdfgen::getFontMetrics(fontMetrics, fontHandle))
    {
        std::fprintf(stderr, "Unable to load font metrics from file '%s'!\n", fontFilePath);
        std::abort();
    }

    const double pixelRange = pixelRange_;

    std::unique_ptr<FontData> fontData = std::make_unique<FontData>();
    fontData->pixelRange = pixelRange;

    double maxWidth = 1.0;

    // Start at 1 so we always force null bytes to be empty
    for(msdfgen::unicode_t key=1; key<0x10000; ++key)
    {

        // No geometry? Don't do any more work!
        double localWidth = 0;
        if( !msdfgen::loadGlyph(fontData->shapes[key], fontHandle, key, &localWidth)
            || fontData->shapes[key].contours.empty())
        {
            continue;
        }

        // Discard dodgey characters
        msdfgen::Shape::Bounds bounds = fontData->shapes[key].getBounds();
        if( bounds.l >= bounds.r
            || bounds.b >= bounds.t
            || !fontData->shapes[key].validate()
        )
        {
            fontData->shapes[key].contours.clear();
            continue;
        }

        if(localWidth > maxWidth)
        {
            maxWidth = localWidth;
        }
    }

    // Determine the rasterization 
    int charWidth  = int(std::round(maxWidth * scale));
    int charHeight = int(std::round(fontMetrics.lineHeight * scale));

    // Pad dimensions with the pixelRange
    fontData->characterWidth     = charWidth + 2 * pixelRange_;
    fontData->characterHeight    = charHeight + 2 * pixelRange_;

    fontData->projection = msdfgen::Projection(
        msdfgen::Vector2(maxWidth/double(charWidth), fontMetrics.lineHeight/double(charHeight)), // scale
        msdfgen::Vector2(pixelRange, -fontMetrics.descenderY * scale + pixelRange)               // translation
    );

    glrefParallelForEach(
        fontData->shapes.begin(),
        fontData->shapes.end(),
        [&](msdfgen::Shape& shape)
        {
            // // TODO: When I figure out how to get SKIA to play nice, uncomment this
            // // and remove the orientContours call.
            // msdfgen::resolveShapeGeometry(fontData->shapes[key]);
            shape.orientContours();
            shape.normalize();
            edgeColoringByDistance(shape, 3.0);
        }
    );

    msdfgen::destroyFont(fontHandle);
    msdfgen::deinitializeFreetype(ftHandle);

    return std::move(fontData);
}


/**
 * @brief Render every character of a font into a dedicated bitmap.
 */
std::unique_ptr<RenderedShapes> renderShapes(const FontData& fontData)
{
    std::unique_ptr<RenderedShapes> renders = std::make_unique<RenderedShapes>();
    const int width = fontData.characterWidth;
    const int height = fontData.characterHeight;
    const double pixelRange = fontData.pixelRange;
    const msdfgen::Projection projection = fontData.projection;

    glrefParallelFor(
        int(0),
        int(0x10000),
        [&](const int idx)
        {
             msdfgen::Bitmap<float, 4> mtsdf (width, height);
             msdfgen::generateMTSDF(mtsdf, fontData.shapes[idx], projection, pixelRange);
             renders->mtsdfRegions[idx] = std::move(mtsdf);
        }
    );

    return std::move(renders);
}


/**
 * @brief Generate the mapping of unique renders to tiles and the per-character
 *        indirect lookup that points to them.
 */
std::unique_ptr<IndirectAndLayers> generateMapping(const RenderedShapes& renders)
{
    std::unique_ptr<IndirectAndLayers> indirectAndLayers = std::make_unique<IndirectAndLayers>();
    indirectAndLayers->indirect = msdfgen::Bitmap<uint16_t, 1>(256, 256);

    const int tileWidth  = renders.mtsdfRegions[0].width();
    const int tileHeight = renders.mtsdfRegions[0].height();
    const int layerWidth  = tileWidth * 32;
    const int layerHeight = tileHeight * 16;

    // This acts as our table of unique tiles we've already written to a layer.
    // [bitmap -> indirectXyz]
    std::unordered_map<
         msdfgen::Bitmap<float, 4>,
         uint16_t,
         HashBitmapHelper,
         EqualBitmapHelper
    >
    writtenTiles;

    uint32_t currentTileX = 0;
    uint32_t currentTileY = 0;
    uint32_t currentTileZ = 0;
    msdfgen::Bitmap<float, 4> currentLayer (layerWidth, layerHeight);

    for(uint32_t regionId=0; regionId<0x10000; ++regionId)
    {
        const uint32_t regionIdX = regionId & 0xff;
              uint32_t regionIdY = (regionId >> 8);

        const msdfgen::Bitmap<float, 4>& region = renders.mtsdfRegions[regionId];

        auto found = writtenTiles.find(region);
        if(found != writtenTiles.end())
        {
            *indirectAndLayers->indirect( int(regionIdX), int(255 - regionIdY) ) = found->second;
            continue;
        }

        // When we have a new unique tile, first we need to copy it's data to the active
        // layer, calculate the indirect coordinates and write it back to our writtenTiles map.

        // Copy scanlines
        for(int y=0; y<tileHeight; ++y)
        {
            const float* src = region(0, y);
            float* dst = currentLayer(
                currentTileX * tileWidth,
                y + (15-currentTileY) * tileHeight  // reverse Y
            );
            std::memcpy(dst, src, sizeof(float)*4*tileWidth);
        }

        uint16_t indirectCoord = packIndirectCoordinate(
            uint8_t(currentTileX),
            uint8_t(currentTileY),
            uint8_t(currentTileZ)
        );

        writtenTiles[region] = indirectCoord;
        *indirectAndLayers->indirect( int(regionIdX), int(255 - regionIdY) ) = indirectCoord;

        // Start a new layer if we're all filled up
        if(++currentTileX >= 32)
        {
            currentTileX = 0;
            if(++currentTileY >= 16)
            {
                currentTileY = 0;
                ++currentTileZ;
                indirectAndLayers->layers.emplace_back(std::move(currentLayer));
                currentLayer = msdfgen::Bitmap<float, 4>(layerWidth, layerHeight);
            }
        }
    }

    // Write an incomplete layer if it's not empty
    if(currentTileX !=0 && currentTileY !=0)
    {
        indirectAndLayers->layers.emplace_back(std::move(currentLayer));
    }

    return std::move(indirectAndLayers);
}


/**
 * @brief Flip Y on indirect and layers (required for OpenGL / Vulkan)
 */
void flipY(IndirectAndLayers& mapping)
{
    glrefParallelInvoke(
        [&]()
        {
            const size_t scanline = 256 * sizeof(uint16_t);
            msdfgen::Bitmap<uint16_t, 1> tmp (256, 256);
            for(int y=0; y<256; ++y)
            {
                const uint16_t* src = mapping.indirect(0, y);
                uint16_t* dst = tmp(0, 255-y);
                std::memcpy(dst, src, scanline);
            }
            mapping.indirect = std::move(tmp);
        },
        [&]()
        {
            glrefParallelForEach(
                mapping.layers.begin(),
                mapping.layers.end(),
                [](msdfgen::Bitmap<float, 4> & layer)
                {
                    const int height = layer.height();
                    const size_t scanline = size_t(layer.width()) * sizeof(float) * 4;
                    msdfgen::Bitmap<float, 4> tmp(layer.width(), height);

                    for(int y=0; y<height; ++y)
                    {
                        const float* src = layer(0, y);
                        float* dst = tmp(0, (height-1)-y);
                        std::memcpy(dst, src, scanline);
                    }

                    layer = std::move(tmp);
                }
            );
        }
    );
}


/**
 * @brief Save in memory representations of indirect and layers to pngs (useful for debugging).
 */
void saveTemps(const IndirectAndLayers& mapping, const std::string& outDir)
{
    const std::string outDirWithSlash = outDir + g_pathSeperator;

    msdfgen::Bitmap<msdfgen::byte, 3> indirectLookup(256, 256);
    for(int y=0; y<256; ++y)
    {
        for(int x=0; x<256; ++x)
        {
            uint16_t packedCoord = *mapping.indirect(x, y);
            uint16_t packedCoordX = packedCoord & ((1 << 5) -1);
            uint16_t packedCoordY = (packedCoord >> 5) & ((1 << 4) -1);
            uint16_t packedCoordZ = packedCoord >> 9;

            msdfgen::byte* outPixel = indirectLookup(x, y);
            outPixel[0] = msdfgen::byte(packedCoordX) << 3;
            outPixel[1] = msdfgen::byte(packedCoordY) << 4;
            outPixel[2] = msdfgen::byte(packedCoordZ) << 1;
        }
    }
    const std::string outIndirectPath = outDirWithSlash + "indirect.png";
    if(!msdfgen::savePng(indirectLookup, outIndirectPath.c_str()))
    {
        std::printf("Warning: Unable to write to: \"%s\" !\n", outIndirectPath.c_str());
    }


    size_t layers = mapping.layers.size();
    for(size_t layer = 0; layer < layers; ++layer)
    {
        const std::string outLayerPath = outDirWithSlash + "layer." + std::to_string(layer) + ".png";
        if(!msdfgen::savePng(mapping.layers[layer], outLayerPath.c_str()))
        {
            std::printf("Warning: Unable to write to: \"%s\" !\n", outLayerPath.c_str());
        }
    }
}


void writePackedData(const IndirectAndLayers& mapping, const std::string& filepath, const uint8_t pixelRange)
{
    FILE* fp = fopen(filepath.c_str(), "wb");

    if(!fp)
    {
        std::printf("Warning: Unable to write to: \"%s\" !\n", filepath.c_str());
        std::abort();
    }

    FontFileHeader fileHeader;
    fileHeader.width = uint16_t(mapping.layers[0].width());
    fileHeader.height = uint16_t(mapping.layers[0].height());
    fileHeader.layers = uint8_t(mapping.layers.size());
    fileHeader.pixelRange = pixelRange;
    fwrite(&fileHeader, sizeof(fileHeader), 1, fp);

    const uint16_t* indirectData = (const uint16_t*)mapping.indirect;
    fwrite(
        indirectData,
        sizeof(uint16_t)*mapping.indirect.width()*mapping.indirect.height(),
        1,
        fp
    );

    const size_t componentsPerLayer = 4 * size_t(fileHeader.width) * size_t(fileHeader.height);
    
    std::vector<msdfgen::byte>  layerBuffer ( componentsPerLayer );
    msdfgen::byte*              layerBufferPtr = &*layerBuffer.begin();

    for(const msdfgen::Bitmap<float, 4>& layer : mapping.layers)
    {
        const float* layerPtr = (const float*)layer;
        for(size_t i=0; i<componentsPerLayer; i+=4)
        {
            uint8_t a = msdfgen::pixelFloatToByte((layerPtr[i+0]));
            uint8_t b = msdfgen::pixelFloatToByte((layerPtr[i+1]));
            uint8_t c = msdfgen::pixelFloatToByte((layerPtr[i+2]));
            uint8_t d = msdfgen::pixelFloatToByte((layerPtr[i+3]));
            layerBufferPtr[i+0] = a;
            layerBufferPtr[i+1] = b;
            layerBufferPtr[i+2] = c;
            layerBufferPtr[i+3] = d;
        }

        fwrite(layerBufferPtr, sizeof(msdfgen::byte)*componentsPerLayer, 1, fp);
    }

    fclose(fp);
}


}  // unnamed namespace



static const char USAGE[] =
R"(Indirect MTSDF UTF8 Gen.

    Usage: indirect-mtsdf-utf8-gen (-i FILE) (-o FILE) [-s SCALE] [-p UINT] [--save-temps DIR] [--directx]

    Options:
      -h --help                      Show this screen.
      -i <file>, --input  <file>     Input TTF file.
      -o <file>, --output <file>     Output indirect + MTSDF texture array file.
      -s <scale>, --scale <scale>    How much to scale the font by. [default: 1]
      -p <range>, --pxrange <range>  Pixel range to sample around. [default: 1]
      --save-temps <dir>             Save the layers and indirect texture into a directory.
      --directx                      Flip Y to start at the top left, rather than bottom left.
)";


int main(int argc, char* argv[])
{
    const auto commandlineArgs = docopt::docopt(USAGE, { argv + 1, argv + argc });

    const std::string& inputFileArg = commandlineArgs.at("--input").asString();
    const std::string& outputFileArg = commandlineArgs.at("--output").asString();
    const std::string& scaleArg = commandlineArgs.at("--scale").asString();
    const std::string& pxRangeArg = commandlineArgs.at("--pxrange").asString();
    const bool directx = commandlineArgs.at("--directx").asBool();

    bool doSaveTemps = false;
    std::string saveTempsDir;
    if(const auto saveTempsArg = commandlineArgs.at("--save-temps"))
    {
        doSaveTemps = true;
        saveTempsDir = saveTempsArg.asString();
    }

    unsigned int pxRange = 1;
    float scale = 1.0;

    if(!pxRangeArg.empty() && (std::sscanf(pxRangeArg.c_str(), "%u", &pxRange) != 1))
    {
        std::fprintf(stderr, "Invalid pxRange (%s)!\n", pxRangeArg.c_str());
        return -1;
    }

    if(pxRange < 0 || pxRange > 255)
    {
        std::fprintf(stderr,
                     "Invalid pxRange (%s)! Must be in the range of [1, 255].\n",
                     pxRangeArg.c_str());
        return -1;
    }

    if(!scaleArg.empty() && ((std::sscanf(scaleArg.c_str(), "%f", &scale) != 1) || (scale <= 0.0)))
    {
        std::fprintf(stderr, "Invalid scale (%s)!\n", scaleArg.c_str());
        return -1;
    }

    if(scale <= 0.0)
    {
        std::fprintf(stderr,
                     "Invalid scale (%s)! Must be greater than 0\n",
                     scaleArg.c_str());
        return -1;
    }

    const bool doFlipY = !directx;

    std::unique_ptr<FontData> fontData = loadFontData(inputFileArg.c_str(),
                                                      scale,
                                                      pxRange);

    std::unique_ptr<RenderedShapes> renderedShapes = renderShapes(*fontData);

    std::unique_ptr<IndirectAndLayers> mapping = generateMapping(*renderedShapes);

    if(doFlipY)
    {
        flipY(*mapping);
    }

    if(doSaveTemps)
    {
        saveTemps(*mapping, saveTempsDir);
    }

    writePackedData(*mapping, outputFileArg, uint8_t(pxRange));

    return 0;
}
