package com.velo.vpn.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.R
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.theme.*

@Composable
fun VeloHeader(showBack: Boolean = false, hearts: Int = 120, onBack: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (showBack) {
                IconButton(onClick = { onBack?.invoke() }) { Icon(Icons.Default.ArrowBack, null) }
                Spacer(Modifier.width(2.dp))
            }
            Image(
                painter = painterResource(R.drawable.velo_logo_mark),
                contentDescription = "Velo",
                modifier = Modifier.size(36.dp)
            )
            Spacer(Modifier.width(7.dp))
            Text("Velo", fontSize = 25.sp, fontWeight = FontWeight.ExtraBold, color = MaterialTheme.colorScheme.onBackground)
        }
        Surface(shape = RoundedCornerShape(16.dp), color = Lilac.copy(alpha = .55f)) {
            Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Favorite, null, tint = HeartPink, modifier = Modifier.size(17.dp))
                Spacer(Modifier.width(5.dp))
                Text(hearts.toString(), fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun VeloCard(modifier: Modifier = Modifier, onClick: (() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    val click = if (onClick != null) modifier.clickable { onClick() } else modifier
    Surface(
        modifier = click,
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 1.5.dp,
        tonalElevation = 0.dp
    ) { Column(Modifier.padding(16.dp), content = content) }
}

@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Button(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().height(55.dp),
        shape = RoundedCornerShape(18.dp),
        colors = ButtonDefaults.buttonColors(containerColor = VeloPurple)
    ) { Text(text, fontSize = 16.sp, fontWeight = FontWeight.Bold) }
}

@Composable
fun FeatureRow(icon: ImageVector, title: String, subtitle: String? = null, onClick: (() -> Unit)? = null, tint: Color = VeloPurple) {
    VeloCard(modifier = Modifier.fillMaxWidth(), onClick = onClick) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).background(Lilac.copy(alpha=.55f), CircleShape), contentAlignment = Alignment.Center) { Icon(icon, null, tint = tint) }
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                if (subtitle != null) Text(subtitle, color = Muted, fontSize = 12.sp)
            }
            if (onClick != null) Icon(Icons.Default.ChevronLeft, null, tint = Muted)
        }
    }
}

data class BottomItem(val route: String, val label: String, val icon: ImageVector)
private val bottomItems = listOf(
    BottomItem(Routes.Home, "خانه", Icons.Default.Home),
    BottomItem(Routes.Gifts, "هدایا", Icons.Default.CardGiftcard),
    BottomItem(Routes.Report, "گزارش", Icons.Default.BarChart),
    BottomItem(Routes.Settings, "تنظیمات", Icons.Default.Settings),
)

@Composable
fun VeloBottomBar(nav: NavHostController, current: String) {
    NavigationBar(containerColor = MaterialTheme.colorScheme.surface, tonalElevation = 1.dp) {
        bottomItems.forEach { item ->
            NavigationBarItem(
                selected = current == item.route,
                onClick = { if (current != item.route) nav.navigate(item.route) { launchSingleTop = true } },
                icon = { Icon(item.icon, null) },
                label = { Text(item.label, fontSize = 11.sp) },
                colors = NavigationBarItemDefaults.colors(indicatorColor = Lilac, selectedIconColor = VeloPurple, selectedTextColor = VeloPurple)
            )
        }
    }
}

@Composable
fun GradientBanner(title: String, subtitle: String, icon: ImageVector, onClick: () -> Unit) {
    Surface(Modifier.fillMaxWidth().clickable(onClick = onClick), shape = RoundedCornerShape(22.dp), color = Color.Transparent) {
        Row(
            Modifier.background(Brush.horizontalGradient(listOf(VeloPurple, SoftPurple))).padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, null, tint = Color.White, modifier = Modifier.size(30.dp))
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Text(subtitle, color = Color.White.copy(alpha=.84f), fontSize = 12.sp)
            }
            Icon(Icons.Default.ChevronLeft, null, tint = Color.White)
        }
    }
}
