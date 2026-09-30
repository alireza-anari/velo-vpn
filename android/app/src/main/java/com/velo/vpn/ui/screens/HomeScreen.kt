package com.velo.vpn.ui.screens

import android.app.Activity.RESULT_OK
import android.net.VpnService
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.WorkspacePremium
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
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloBottomBar
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Lilac
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun HomeScreen(nav: NavHostController, vm: VeloViewModel, accountVm: AccountViewModel) {
    val state by vm.home.collectAsState()
    val account by accountVm.state.collectAsState()
    val context = LocalContext.current
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
            text = { Text("با ادامه، اتصال دستگاه قبلی قطع و این دستگاه فعال می‌شود.") },
            confirmButton = { TextButton(onClick = { vm.clearNotice(); vm.connect(forceTakeover = true) }) { Text("اتصال این دستگاه") } },
            dismissButton = { TextButton(onClick = vm::clearNotice) { Text("انصراف") } },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = { VeloBottomBar(nav, Routes.Home) },
    ) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(horizontal = 20.dp, vertical = 18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            VeloHeader()
            Spacer(Modifier.height(8.dp))

            Text(
                when {
                    !account.loggedIn -> "ورود به Velo"
                    !account.subscriptionActive -> "اشتراک پریمیوم لازم است"
                    state.connected -> "متصل"
                    else -> "آماده اتصال"
                },
                fontSize = 23.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            Text(
                when {
                    !account.loggedIn -> "با ایمیل وارد شوید تا اشتراک شما فعال شود."
                    !account.subscriptionActive -> "پس از خرید و تأیید، اتصال پریمیوم فعال می‌شود."
                    state.connected -> state.serverName
                    else -> "بهترین سرور به‌صورت خودکار انتخاب می‌شود."
                },
                color = Muted,
                fontSize = 13.sp,
            )

            Spacer(Modifier.height(4.dp))

            Box(
                Modifier.size(210.dp).background(Lilac.copy(alpha = .40f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Box(
                    Modifier.size(168.dp).background(MaterialTheme.colorScheme.surface, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    IconButton(
                        enabled = !state.busy && state.ready && account.loggedIn && account.subscriptionActive,
                        onClick = {
                            if (state.connected) {
                                vm.disconnect()
                            } else {
                                val prepare = VpnService.prepare(context)
                                if (prepare != null) vpnPermission.launch(prepare) else vm.connect()
                            }
                        },
                        modifier = Modifier.size(116.dp).background(if (state.connected) VeloPurple else Color.Transparent, CircleShape),
                    ) {
                        if (state.busy) {
                            CircularProgressIndicator(modifier = Modifier.size(36.dp), color = VeloPurple)
                        } else {
                            Icon(
                                if (account.subscriptionActive) Icons.Default.PowerSettingsNew else Icons.Default.Lock,
                                null,
                                tint = if (state.connected) Color.White else VeloPurple,
                                modifier = Modifier.size(54.dp),
                            )
                        }
                    }
                }
            }

            if (!account.loggedIn) {
                PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
            } else if (!account.subscriptionActive) {
                PrimaryButton("خرید اشتراک پریمیوم") { nav.navigate(Routes.Premium) }
                TextButton(onClick = { accountVm.refresh() }) { Text("اشتراکم فعال شده؛ بررسی مجدد") }
            } else {
                VeloCard(Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.WorkspacePremium, null, tint = VeloPurple)
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("پریمیوم فعال", fontWeight = FontWeight.Bold)
                            Text(account.subscriptionEndsAt?.take(10)?.let { "تا " + it } ?: "فعال", color = Muted, fontSize = 12.sp)
                        }
                    }
                }

                VeloCard(Modifier.fillMaxWidth(), onClick = { nav.navigate(Routes.Report) }) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.BarChart, null, tint = VeloPurple)
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("گزارش مصرف", fontWeight = FontWeight.Bold)
                            Text("حجم و زمان استفاده", color = Muted, fontSize = 12.sp)
                        }
                    }
                }
            }
        }
    }
}
