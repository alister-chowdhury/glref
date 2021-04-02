from OpenGL.GLUT import *


__all__ = ("Window",)

class Window(object):

    LEFT = GLUT_LEFT_BUTTON
    MIDDLE = GLUT_MIDDLE_BUTTON
    RIGHT = GLUT_RIGHT_BUTTON

    UP = GLUT_UP
    DOWN = GLUT_DOWN

    def __init__(self, width=1024, height=512):

        self.width = width
        self.height = height

        self.title = b"Renderer"

        self.on_init = None
        self.on_draw = None
        self.on_idle = None
        self.on_resize = None
        self.on_keypress = None
        self.on_mouse = None
        self.on_drag = None

        self._last_drag_x = 0
        self._last_drag_y = 0

    def run(self):
        glutInitContextVersion(4, 6)
        glutInitContextProfile(GLUT_CORE_PROFILE)
        glutInitContextFlags(GLUT_FORWARD_COMPATIBLE)
        glutInit()
        glutInitDisplayMode(GLUT_RGBA|GLUT_DEPTH|GLUT_STENCIL|GLUT_DOUBLE)
        glutInitWindowSize(self.width, self.height)

        glutCreateWindow(self.title)
        glutReshapeFunc(self._resize)
        glutDisplayFunc(self._draw)
        if self.on_idle:
            glutIdleFunc(self._idle)
        glutKeyboardFunc(self._keypress)
        glutMouseFunc(self._mouse)
        glutMotionFunc(self._drag)

        if self.on_init:
            self.on_init(self)

        glutMainLoop()

    def redraw(self):
        glutPostRedisplay()


    def _draw(self):
        if self.on_draw:
            self.on_draw(self)
            glutSwapBuffers()

    def _resize(self, width, height):
        self.width = width
        self.height = height
        if self.on_resize:
            self.on_resize(self, width, height)

    def _idle(self):
        if self.on_idle:
            self.on_idle(self)

    def _keypress(self, key, x, y):
        if self.on_keypress:
            self.on_keypress(self, key, x, y)

    def _mouse(self, button, state, x, y):
        if self.on_drag and state == self.DOWN:
            self._last_drag_x = x
            self._last_drag_y = y
            self._mouse_button = button

        if self.on_mouse:
            self.on_mouse(self, button, state, x, y)

    def _drag(self, x, y):
        if self.on_drag:
            deriv_x = x - self._last_drag_x
            deriv_y = y - self._last_drag_y
            self.on_drag(self, deriv_x, deriv_y, self._mouse_button)
            self._last_drag_x = x
            self._last_drag_y = y
