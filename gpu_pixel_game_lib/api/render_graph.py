class DrawCommand(object):
    def __init__(
        self,
        vertex_count,
        instance_count,
        first_vertex,
        first_instance,
        modified_by_shaders=False,
        clear_every_frame=None,
        vertex_count_filter=None,
        instance_count_filter=None,
        first_vertex_filter=None,
        first_instance_filter=None,
    ):
        self.vertex_count = vertex_count
        self.instance_count = instance_count
        self.first_vertex = first_vertex
        self.first_instance = first_instance
        self.modified_by_shaders = modified_by_shaders
        self.clear_every_frame = clear_every_frame

        self.vertex_count_filter = vertex_count_filter
        self.instance_count_filter = instance_count_filter
        self.first_vertex_filter = first_vertex_filter
        self.first_instance_filter = first_instance_filter

        self.used = False
        self.resolved_offset = None

    def collect_filters(self):
        result = []
        if self.vertex_count_filter is not None:
            result.append[0, self.vertex_count_filter]
        if self.instance_count_filter is not None:
            result.append[1, self.instance_count_filter]
        if self.first_vertex_filter is not None:
            result.append[2, self.first_vertex_filter]
        if self.first_instance_filter is not None:
            result.append[3, self.first_instance_filter]
        return result

    def serialize(self):
        return [
            self.vertex_count,
            self.instance_count,
            self.first_vertex,
            self.first_instance,
        ]


class DrawIndexedCommand(object):
    def __init__(
        self,
        index_count,
        instance_count,
        first_index,
        vertex_offset,
        first_instance,
        modified_by_shaders=False,
        clear_every_frame=None,
        index_count_filter=None,
        instance_count_filter=None,
        first_index_filter=None,
        vertex_offset_filter=None,
        first_instance_filter=None,
    ):
        self.index_count = index_count
        self.instance_count = instance_count
        self.first_index = first_index
        self.vertex_offset = vertex_offset
        self.first_instance = first_instance
        self.modified_by_shaders = modified_by_shaders
        self.clear_every_frame = clear_every_frame

        self.index_count_filter = index_count_filter
        self.instance_count_filter = instance_count_filter
        self.first_index_filter = first_index_filter
        self.vertex_offset_filter = vertex_offset_filter
        self.first_instance_filter = first_instance_filter

        self.used = False
        self.resolved_offset = None

    def collect_filters(self):
        result = []
        if self.index_count_filter is not None:
            result.append[0, self.index_count_filter]
        if self.instance_count_filter is not None:
            result.append[1, self.instance_count_filter]
        if self.first_index_filter is not None:
            result.append[2, self.first_index_filter]
        if self.vertex_offset_filter is not None:
            result.append[3, self.vertex_offset_filter]
        if self.first_instance_filter is not None:
            result.append[4, self.first_instance_filter]
        return result

    def serialize(self):
        return [
            self.index_count,
            self.instance_count,
            self.first_index,
            self.vertex_offset,
            self.first_instance,
        ]


class DispatchCommand(object):
    def __init__(
        self,
        x,
        y,
        z,
        first_instance,
        modified_by_shaders=False,
        clear_every_frame=None,
        x_filter=None,
        y_filter=None,
        z_filter=None,
        first_instance_filter=None,
    ):
        self.x = x
        self.y = y
        self.z = z

        self.x_filter = x_filter
        self.y_filter = y_filter
        self.z_filter = z_filter

        self.used = False
        self.resolved_offset = None

    def collect_filters(self):
        result = []
        if self.x_filter is not None:
            result.append[0, self.x_filter]
        if self.y_filter is not None:
            result.append[1, self.y_filter]
        if self.z_filter is not None:
            result.append[2, self.z_filter]
        return result

    def serialize(self):
        return [self.x, self.y, self.z]


class RenderGraphBuilder(object):
    DrawCommand = DrawCommand
    DrawIndexedCommand = DrawIndexedCommand
    DispatchComputeCommand = DispatchComputeCommand

    def __init__(self):
        self._indirect_commands = set()
        self._dispatch_commands = []

    def _add_indirect(self, command):
        if not isinstance(
            command, (DrawCommand, DrawIndexedCommand, DispatchComputeCommand)
        ):
            raise ValueError(
                "Unsupport command type: {0}".format(type(command))
            )
        self._indirect_commands.add(command)

    def draw(self, command, parameters, vertex_shader, fragment_shader):
        if not isinstance(command, DrawCommand):
            raise ValueError(
                "draw was provided a command that isn't DrawCommand! ({0})".format(
                    type(command)
                )
            )
        self._add_indirect(command)
        self._dispatch_commands.append(
            {
                "command": command,
                "parameters": parameters,
                "type": "draw",
                "shaders": {
                    "vs": vertex_shader,
                    "fs": fragment_shader,
                },
            }
        )
