class This object gives access to off screen buffers.:
    """bind(save=True)
    draw_view3d(scene, view3d, region, modelview_matrix, projection_matrix)
    free()
    unbind(restore=True)
    """

    color_texture = None
    """Color texture.
    
    :type: int
    """

    height = None
    """Texture height.
    
    :type: int
    """

    width = None
    """Texture width.
    
    :type: int
    """
