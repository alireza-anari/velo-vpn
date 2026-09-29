package com.velo.vpn.ui.screens

import android.app.Activity
import android.app.Activity.RESULT_OK
import android.net.VpnService
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.VeloViewModel
import com.velo.vpn.ui.components.*
import com.velo.vpn.ui.theme.*

@Composable
fun HomeScreen(nav: NavHostController, vm: VeloViewModel, accountVm: AccountViewModel) {
    val state by vm.home.collectAsState()
    val account by accountVm.state.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity
    val snackbar = remember { SnackbarHostState() }

    val vpnPermission = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) vm.connect()
    }

    LaunchedEffect(state.error, state.info) {
        val message = state.error ?: state.info
        if (!message.isNullOrBlank()) {
            snackbar.showSnackbar(message)
            vm.clearNotice()
        }
    }

    if (state.takeoverRequired) {
        AlertDialog(
            onDismissRequest = vm::clearNotice,
            title = { Text("اشتراک روی دستگاه دیگری فعال است") },
            text = { Text("می‌خواهید اتصال دستگاه دیگر قطع شود و این دستگاه متصل شود؟") },
            confirmButton = { TextButton(onClick = { vm.clearNotice(); vm.connect(forceTakeover = true) }) { Text("اتصال این دستگاه") } },
            dismissButton = { TextButton(onClick = vm::clearNotice) { Text("انصراف") } },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = { VeloBottomBar(nav, Routes.Home) },
    ) { pad ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(pad)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp)
                .padding(top = 18.dp, bottom = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            VeloHeader(hearts = account.hearts)
            Spacer(Modifier.height(4.dp))

            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Box(
                    Modifier.size(190.dp).background(Lilac.copy(alpha = .45f), CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Box(
                        Modifier.size(155.dp).background(MaterialTheme.colorScheme.surface, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        IconButton(
                            enabled = !state.busy && state.ready,
                            onClick = {
                                if (state.connected) {
                                    vm.disconnect()
                                } else {
                                    val prepare = VpnService.prepare(context)
                                    if (prepare != null) vpnPermission.launch(prepare) else vm.connect()
                                }
                            },
                            modifier = Modifier
                                .size(110.dp)
                                .background(if (state.connected) VeloPurple else Color.Transparent, CircleShape),
                        ) {
                            if (state.busy) {
                                CircularProgressIndicator(modifier = Modifier.size(38.dp), color = VeloPurple)
                            } else {
                                Icon(
                                    Icons.Default.PowerSettingsNew,
                                    null,
                                    tint = if (state.connected) Color.White else VeloPurple,
                                    modifier = Modifier.size(54.dp),
                                )
                            }
                        }
                    }
                }
            }
            Text(
                if (state.connected) "متصل" else "اتصال",
                Modifier.align(Alignment.CenterHorizontally),
                fontWeight = FontWeight.Bold,
                fontSize = 23.sp,
            )
            Text(
                if (state.connected) "Velo آماده استفاده است" else "برای شروع لمس کنید",
                Modifier.align(Alignment.CenterHorizontally),
                color = Muted,
                fontSize = 13.sp,
            )

            VeloCard(modifier = Modifier.fillMaxWidth(), onClick = { nav.navigate(Routes.Servers) }) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(countryFlag(state.serverCountryCode), fontSize = 28.sp)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(state.serverName, fontWeight = FontWeight.Bold)
                        Text(if (state.premium) "سرور انتخابی شما" else "انتخاب خودکار Velo", color = Muted, fontSize = 12.sp)
                    }
                    Icon(Icons.Default.ChevronLeft, null, tint = Muted)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MiniStat(
                    "سرعت",
                    if (state.premium) "کامل" else "${state.freeSpeedMbps} Mbps",
                    Icons.Default.Speed,
                    Modifier.weight(1f),
                )
                MiniStat(
                    "زمان باقی‌مانده",
                    if (state.premium) "نامحدود" else formatTime(state.remainingSeconds),
                    Icons.Default.Schedule,
                    Modifier.weight(1f),
                )
            }

            GradientBanner(
                "دریافت زمان رایگان",
                if (state.adBusy) "در حال آماده‌سازی ویدیو…" else "هر ویدیو +${state.adRewardMinutes} دقیقه",
                Icons.Default.CardGiftcard,
            ) {
                if (activity != null && !state.adBusy) vm.watchRewardedAd(activity)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                FeatureTile("دعوت دوستان", "دریافت پاداش", Icons.Default.GroupAdd, Modifier.weight(1f)) { nav.navigate(Routes.Referral) }
                FeatureTile("خرید پریمیوم", "سرعت کامل", Icons.Default.WorkspacePremium, Modifier.weight(1f)) { nav.navigate(Routes.Premium) }
            }
        }
    }
}

private fun formatTime(seconds: Int): String {
    val h = seconds / 3600
    val m = (seconds % 3600) / 60
    val s = seconds % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%02d:%02d".format(m, s)
}

private fun countryFlag(code: String): String = when (code.uppercase()) {
    "DE" -> "🇩🇪"
    "TR" -> "🇹🇷"
    "US" -> "🇺🇸"
    "NL" -> "🇳🇱"
    "FR" -> "🇫🇷"
    else -> "🌐"
}

@Composable
private fun MiniStat(label: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector, modifier: Modifier) {
    VeloCard(modifier = modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = VeloPurple)
            Spacer(Modifier.width(8.dp))
            Column {
                Text(label, color = Muted, fontSize = 11.sp)
                Text(value, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun FeatureTile(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    VeloCard(modifier, onClick) {
        Icon(icon, null, tint = VeloPurple)
        Spacer(Modifier.height(9.dp))
        Text(title, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Muted, fontSize = 11.sp)
    }
}
