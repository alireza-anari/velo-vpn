package com.velo.vpn.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.ReportViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.VeloBottomBar
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.SoftPurple
import com.velo.vpn.ui.theme.VeloPurple
import kotlin.math.max

@Composable
fun ReportScreen(nav: NavHostController, vm: ReportViewModel) {
    val state by vm.state.collectAsState()
    val report = state.report
    Scaffold(bottomBar = { VeloBottomBar(nav, Routes.Report) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            VeloHeader()
            Text("مصرف", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold)
            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ReportStat(formatBytes((report?.todayRxBytes ?: 0) + (report?.todayTxBytes ?: 0)), "امروز", Icons.Default.Download, Modifier.weight(1f))
                ReportStat(formatDuration(report?.todaySeconds ?: 0), "زمان امروز", Icons.Default.Schedule, Modifier.weight(1f))
                ReportStat((report?.todayConnections ?: 0).toString(), "اتصال", Icons.Default.Link, Modifier.weight(1f))
            }

            VeloCard(Modifier.fillMaxWidth()) {
                Text("۷ روز گذشته", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Spacer(Modifier.height(18.dp))
                val days = report?.last7Days.orEmpty()
                val values = if (days.isEmpty()) List(7) { 0L } else days.map { it.bytes }
                val peak = max(1L, values.maxOrNull() ?: 1L)
                Row(
                    Modifier.fillMaxWidth().height(150.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    values.forEachIndexed { i, bytes ->
                        val fraction = (bytes.toFloat() / peak.toFloat()).coerceIn(.05f, 1f)
                        Column(
                            Modifier.weight(1f),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Bottom,
                        ) {
                            Box(
                                Modifier.fillMaxWidth().fillMaxHeight(fraction)
                                    .background(if (i == values.lastIndex) VeloPurple else SoftPurple, RoundedCornerShape(8.dp))
                            )
                            Spacer(Modifier.height(5.dp))
                            Text(listOf("ج", "پ", "چ", "د", "س", "ش", "ی").getOrElse(i) { "" }, fontSize = 10.sp, color = Muted)
                        }
                    }
                }
            }

            VeloCard(Modifier.fillMaxWidth()) {
                Text("این ماه", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(14.dp))
                Row {
                    Column(Modifier.weight(1f)) {
                        Text(formatBytes(report?.monthBytes ?: 0), fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Text("حجم مصرف", color = Muted, fontSize = 11.sp)
                    }
                    Column(Modifier.weight(1f)) {
                        Text(formatDuration(report?.monthSeconds ?: 0), fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Text("زمان اتصال", color = Muted, fontSize = 11.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun ReportStat(value: String, label: String, icon: ImageVector, modifier: Modifier) {
    VeloCard(modifier) {
        Icon(icon, null, tint = VeloPurple)
        Spacer(Modifier.height(10.dp))
        Text(value, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(label, fontSize = 10.sp, color = Muted)
    }
}

private fun formatBytes(bytes: Long): String {
    val gb = bytes / 1_073_741_824.0
    val mb = bytes / 1_048_576.0
    return if (gb >= 1.0) String.format("%.1f GB", gb) else String.format("%.0f MB", mb)
}

private fun formatDuration(seconds: Int): String {
    val h = seconds / 3600
    val m = (seconds % 3600) / 60
    return if (h > 0) h.toString() + "س " + m.toString() + "د" else m.toString() + " دقیقه"
}
