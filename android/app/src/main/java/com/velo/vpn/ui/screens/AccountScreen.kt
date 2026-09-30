package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloBottomBar
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun AccountScreen(nav: NavHostController, vm: AccountViewModel) {
    val state by vm.state.collectAsState()
    var email by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }

    Scaffold(bottomBar = { VeloBottomBar(nav, Routes.Account) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            VeloHeader()
            Text("حساب", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold)

            if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())

            if (state.loggedIn) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("ایمیل", color = Muted, fontSize = 12.sp)
                    Text(state.email, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                    Spacer(Modifier.height(18.dp))
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Icon(Icons.Default.WorkspacePremium, null, tint = VeloPurple)
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text(if (state.subscriptionActive) "اشتراک پریمیوم فعال" else "اشتراک فعال ندارید", fontWeight = FontWeight.Bold)
                            state.subscriptionEndsAt?.let { Text("تا " + it.take(10), color = Muted, fontSize = 11.sp) }
                        }
                    }
                }

                if (!state.subscriptionActive) {
                    PrimaryButton("خرید اشتراک") { nav.navigate(Routes.Premium) }
                }
                OutlinedButton(onClick = { vm.refresh() }, modifier = Modifier.fillMaxWidth()) { Text("بروزرسانی وضعیت اشتراک") }
                TextButton(onClick = { vm.logout() }, modifier = Modifier.fillMaxWidth()) { Text("خروج از حساب") }
            } else if (!state.otpSent) {
                Text("برای خرید و استفاده از اشتراک پریمیوم با ایمیل وارد شوید.", color = Muted)
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("ایمیل") },
                    leadingIcon = { Icon(Icons.Default.Email, null) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    singleLine = true,
                )
                PrimaryButton("ارسال کد ورود") { vm.requestOtp(email) }
            } else {
                Text("کد ۶ رقمی ارسال‌شده به " + state.pendingEmail + " را وارد کنید.", color = Muted)
                OutlinedTextField(
                    value = code,
                    onValueChange = { code = it.filter(Char::isDigit).take(6) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("کد ورود") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    singleLine = true,
                )
                if (state.devCode != null) Text("کد توسعه: " + state.devCode, color = Muted, fontSize = 11.sp)
                PrimaryButton("ورود") { vm.verifyOtp(code) { nav.navigate(Routes.Home) { popUpTo(Routes.Home) { inclusive = false } } } }
                TextButton(onClick = { vm.clearNotice(); vm.requestOtp(state.pendingEmail) }) { Text("ارسال دوباره کد") }
            }

            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            state.info?.let { Text(it, color = VeloPurple) }
        }
    }
}
