package com.velo.vpn.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = VeloPurple,
    secondary = SoftPurple,
    background = Mist,
    surface = androidx.compose.ui.graphics.Color.White,
    onPrimary = androidx.compose.ui.graphics.Color.White,
    onBackground = Ink,
    onSurface = Ink
)

private val DarkColors = darkColorScheme(
    primary = SoftPurple,
    secondary = VeloPurple,
    background = DarkBg,
    surface = DarkSurface,
    onPrimary = DeepPurple,
    onBackground = androidx.compose.ui.graphics.Color(0xFFF7F3FF),
    onSurface = androidx.compose.ui.graphics.Color(0xFFF7F3FF)
)

@Composable
fun VeloTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (darkTheme) DarkColors else LightColors, content = content)
}
